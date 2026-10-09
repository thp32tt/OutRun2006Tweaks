#pragma once
// R186: dormant native DrawIndexed triangle-list readiness for owned DEFAULT VB/IB.
// Does not route D3D9 gameplay or submit any D3D11 Draw. WARP-only proof in tools.
#include "native_linear_buffer_mirror.hpp"
#include <cstdint>
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_indexed_linear_draw_ready(
    const NativeLinearBufferMirror& vertexOwner,
    const NativeLinearBufferMirror& indexOwner,
    ID3D11DeviceContext* context,
    UINT startIndex, UINT indexCount, INT baseVertexLocation,
    std::uint64_t deviceGeneration,
    std::uint64_t vertexSnapshotVersion,
    std::uint64_t indexSnapshotVersion) noexcept {
    if (!context || indexCount % 3u != 0 ||
        !vertexOwner.indexed_draw_bounds_exact(
            indexOwner, context, startIndex, indexCount, baseVertexLocation,
            deviceGeneration, vertexSnapshotVersion, indexSnapshotVersion))
        return false;

    D3D11_PRIMITIVE_TOPOLOGY topology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    context->IAGetPrimitiveTopology(&topology);
    if (topology != D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST)
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

    Microsoft::WRL::ComPtr<ID3D11Device> device;
    context->GetDevice(device.GetAddressOf());
    if (!device)
        return false;
    // A live native IA snapshot is insufficient if unrelated shaders/RTV are
    // rebound. Every draw-critical object must be owned by this same device.
    const auto sameDevice = [&](ID3D11DeviceChild* object) noexcept {
        if (!object) return false;
        Microsoft::WRL::ComPtr<ID3D11Device> owner;
        object->GetDevice(owner.GetAddressOf());
        return owner.Get() == device.Get();
    };
    if (!sameDevice(layout.Get()) || !sameDevice(vs.Get()) ||
        !sameDevice(ps.Get()) || !sameDevice(rtv.Get()))
        return false;

    // Activation is intentionally out of scope: no DrawIndexed dispatch here.
    return true;
}
} // namespace outrun::vr::dx11
