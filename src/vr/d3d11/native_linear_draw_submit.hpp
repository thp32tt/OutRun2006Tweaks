#pragma once
// R185: dormant native non-indexed Draw readiness/ownership fence.
// No game hook enables this path. No native Draw call lives here. Reject uncertainty
// against stale D3D9 DEFAULT snapshots or unrelated D3D11 state.
#include "native_linear_buffer_mirror.hpp"
#include <cstdint>
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_linear_draw_ready(
    const NativeLinearBufferMirror& vertexOwner,
    ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount,
    std::uint64_t deviceGeneration,
    std::uint64_t sourceSnapshotVersion) noexcept {
    if (!context || !vertexCount ||
        !vertexOwner.binding_exact(
            context, deviceGeneration, sourceSnapshotVersion))
        return false;

    ID3D11Buffer* const native = vertexOwner.buffer();
    if (!native) return false;
    D3D11_BUFFER_DESC desc{};
    native->GetDesc(&desc);
    Microsoft::WRL::ComPtr<ID3D11Buffer> liveVertex;
    UINT stride = 0, offset = 1;
    context->IAGetVertexBuffers(0, 1, liveVertex.GetAddressOf(), &stride, &offset);
    if (liveVertex.Get() != native || !stride || offset != 0 ||
        desc.ByteWidth % stride != 0)
        return false;
    const UINT capacity = desc.ByteWidth / stride;
    if (startVertex >= capacity || vertexCount > capacity - startVertex)
        return false;

    // Only the proven triangle-list path is admitted. Primitive conversion,
    // strip/fan expansion and other layouts require separately owned gates.
    D3D11_PRIMITIVE_TOPOLOGY topology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    context->IAGetPrimitiveTopology(&topology);
    if (topology != D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST ||
        vertexCount % 3u != 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11InputLayout> layout;
    Microsoft::WRL::ComPtr<ID3D11VertexShader> vs;
    Microsoft::WRL::ComPtr<ID3D11PixelShader> ps;
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv;
    context->IAGetInputLayout(layout.GetAddressOf());
    context->VSGetShader(vs.GetAddressOf(), nullptr, nullptr);
    context->PSGetShader(ps.GetAddressOf(), nullptr, nullptr);
    context->OMGetRenderTargets(1, rtv.GetAddressOf(), nullptr);
    if (!layout || !vs || !ps || !rtv)
        return false;

    // IA identity above already proves immediate context + VB device.
    // A complete pipeline must belong to that identical native device.
    Microsoft::WRL::ComPtr<ID3D11Device> device, objectDevice;
    context->GetDevice(device.GetAddressOf());
    if (!device) return false;
    layout->GetDevice(objectDevice.GetAddressOf());
    if (objectDevice.Get() != device.Get()) return false;
    objectDevice.Reset();
    vs->GetDevice(objectDevice.GetAddressOf());
    if (objectDevice.Get() != device.Get()) return false;
    objectDevice.Reset();
    ps->GetDevice(objectDevice.GetAddressOf());
    if (objectDevice.Get() != device.Get()) return false;
    objectDevice.Reset();
    rtv->GetDevice(objectDevice.GetAddressOf());
    if (objectDevice.Get() != device.Get()) return false;

    // Deliberately no D3D11 Draw* dispatch in production source. Only an
    // isolated WARP probe may consume this readiness result until an explicit
    // game-native activation/runtime review authorizes dispatch.
    return true;
}
} // namespace outrun::vr::dx11
