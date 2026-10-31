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
    // R197: translated D3D9 non-indexed triangle lists have no GS/HS/DS.
    // A retained stage can alter/discard vertices without changing owned VB
    // or VS/PS; do not claim safe native Draw until all three are unbound.
    Microsoft::WRL::ComPtr<ID3D11GeometryShader> gs;
    Microsoft::WRL::ComPtr<ID3D11HullShader> hs;
    Microsoft::WRL::ComPtr<ID3D11DomainShader> ds;
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv;
    context->IAGetInputLayout(layout.GetAddressOf());
    context->VSGetShader(vs.GetAddressOf(), nullptr, nullptr);
    context->PSGetShader(ps.GetAddressOf(), nullptr, nullptr);
    context->GSGetShader(gs.GetAddressOf(), nullptr, nullptr);
    context->HSGetShader(hs.GetAddressOf(), nullptr, nullptr);
    context->DSGetShader(ds.GetAddressOf(), nullptr, nullptr);
    context->OMGetRenderTargets(1, rtv.GetAddressOf(), nullptr);
    if (gs || hs || ds) return false;
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

// R209: opt-in exact pipeline identity for dormant non-indexed native Draw.
// R185's same-device prerequisite cannot reject a different object made on
// that same device (e.g. a re-bound PS or another eye RTV). The caller must
// provide the exact original pipeline objects, never just a compatible device.
// This helper only verifies; it cannot activate a gameplay D3D11 Draw.
[[nodiscard]] inline bool verified_linear_pipeline_identity_ready(
    const NativeLinearBufferMirror& vertexOwner,
    ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount,
    std::uint64_t deviceGeneration,
    std::uint64_t sourceSnapshotVersion,
    ID3D11InputLayout* expectedLayout,
    ID3D11VertexShader* expectedVs,
    ID3D11PixelShader* expectedPs,
    ID3D11RenderTargetView* expectedRtv) noexcept {
    if (!expectedLayout || !expectedVs || !expectedPs || !expectedRtv ||
        !verified_linear_draw_ready(
            vertexOwner, context, startVertex, vertexCount,
            deviceGeneration, sourceSnapshotVersion))
        return false;
    Microsoft::WRL::ComPtr<ID3D11InputLayout> layout;
    Microsoft::WRL::ComPtr<ID3D11VertexShader> vs;
    Microsoft::WRL::ComPtr<ID3D11PixelShader> ps;
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv;
    context->IAGetInputLayout(layout.GetAddressOf());
    context->VSGetShader(vs.GetAddressOf(), nullptr, nullptr);
    context->PSGetShader(ps.GetAddressOf(), nullptr, nullptr);
    context->OMGetRenderTargets(1, rtv.GetAddressOf(), nullptr);
    return layout.Get() == expectedLayout &&
           vs.Get() == expectedVs &&
           ps.Get() == expectedPs &&
           rtv.Get() == expectedRtv;
}

// R210: dormant depth-aware non-indexed Draw additionally seals live OM DSV
// and depth-stencil state identity. Same-device but foreign depth views may
// reject pixels while the R209 IA/VS/PS/RTV evidence remains unchanged.
// Deliberately narrow: only explicit LESS/write-all/no-stencil passes.
// No game-native Draw dispatch or implicit activation occurs here.
[[nodiscard]] inline bool verified_linear_depth_om_identity_ready(
    const NativeLinearBufferMirror& vertexOwner,
    ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount,
    std::uint64_t deviceGeneration,
    std::uint64_t sourceSnapshotVersion,
    ID3D11InputLayout* expectedLayout,
    ID3D11VertexShader* expectedVs,
    ID3D11PixelShader* expectedPs,
    ID3D11RenderTargetView* expectedRtv,
    ID3D11DepthStencilView* expectedDsv,
    ID3D11DepthStencilState* expectedDepthState) noexcept {
    if (!context || !expectedDsv || !expectedDepthState ||
        !verified_linear_pipeline_identity_ready(
            vertexOwner, context, startVertex, vertexCount,
            deviceGeneration, sourceSnapshotVersion,
            expectedLayout, expectedVs, expectedPs, expectedRtv))
        return false;
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> liveRtv;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilView> liveDsv;
    context->OMGetRenderTargets(1, liveRtv.GetAddressOf(), liveDsv.GetAddressOf());
    if (liveRtv.Get() != expectedRtv || liveDsv.Get() != expectedDsv)
        return false;

    Microsoft::WRL::ComPtr<ID3D11DepthStencilState> liveDepthState;
    UINT stencilRef = ~0u;
    context->OMGetDepthStencilState(liveDepthState.GetAddressOf(), &stencilRef);
    if (liveDepthState.Get() != expectedDepthState || stencilRef != 0)
        return false;
    D3D11_DEPTH_STENCIL_DESC desc{};
    expectedDepthState->GetDesc(&desc);
    if (!desc.DepthEnable || desc.DepthWriteMask != D3D11_DEPTH_WRITE_MASK_ALL ||
        desc.DepthFunc != D3D11_COMPARISON_LESS || desc.StencilEnable)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice, ownerDevice;
    context->GetDevice(contextDevice.GetAddressOf());
    if (!contextDevice) return false;
    expectedDsv->GetDevice(ownerDevice.GetAddressOf());
    if (ownerDevice.Get() != contextDevice.Get()) return false;
    ownerDevice.Reset();
    expectedDepthState->GetDevice(ownerDevice.GetAddressOf());
    return ownerDevice.Get() == contextDevice.Get();
}

// R211: an exact depth-aware linear eye cannot have another OM color output.
// R210 verifies RTV slot 0, but a retained MRT slot 1+ can receive an
// unintended native shader SV_TargetN write into a different eye. Opt-in,
// fail-closed; all OMGetRenderTargets references are released on every path.
// Still no production D3D11 Draw dispatch or gameplay activation.
[[nodiscard]] inline bool verified_linear_single_eye_depth_draw_ready(
    const NativeLinearBufferMirror& vertexOwner,
    ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount,
    std::uint64_t deviceGeneration,
    std::uint64_t sourceSnapshotVersion,
    ID3D11InputLayout* expectedLayout,
    ID3D11VertexShader* expectedVs,
    ID3D11PixelShader* expectedPs,
    ID3D11RenderTargetView* expectedRtv,
    ID3D11DepthStencilView* expectedDsv,
    ID3D11DepthStencilState* expectedDepthState) noexcept {
    if (!verified_linear_depth_om_identity_ready(
            vertexOwner, context, startVertex, vertexCount,
            deviceGeneration, sourceSnapshotVersion,
            expectedLayout, expectedVs, expectedPs,
            expectedRtv, expectedDsv, expectedDepthState))
        return false;
    ID3D11RenderTargetView* outputs[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT] = {};
    context->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
                                outputs, nullptr);
    bool singleEye = outputs[0] == expectedRtv;
    for (UINT slot = 1; slot < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++slot)
        if (outputs[slot]) singleEye = false;
    for (auto* output : outputs)
        if (output) output->Release();
    return singleEye;
}

// R214: strict opaque non-indexed native Draw requires one exact depth eye,
// exact IA/VS/PS/RTV/DSV and unmodified live OM sample coverage. R211 alone
// allows a retained blend to erase pixels or a zero sample mask to suppress
// all samples. This is readiness-only; no gameplay Draw is dispatched here.
[[nodiscard]] inline bool verified_linear_opaque_single_eye_draw_ready(
    const NativeLinearBufferMirror& vertexOwner,
    ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount,
    std::uint64_t deviceGeneration, std::uint64_t sourceSnapshotVersion,
    ID3D11InputLayout* expectedLayout,
    ID3D11VertexShader* expectedVs,
    ID3D11PixelShader* expectedPs,
    ID3D11RenderTargetView* expectedRtv,
    ID3D11DepthStencilView* expectedDsv,
    ID3D11DepthStencilState* expectedDepthState) noexcept {
    if (!context || !verified_linear_single_eye_depth_draw_ready(
            vertexOwner, context, startVertex, vertexCount,
            deviceGeneration, sourceSnapshotVersion,
            expectedLayout, expectedVs, expectedPs,
            expectedRtv, expectedDsv, expectedDepthState))
        return false;
    // No explicit blend object is accepted, even if it currently happens to
    // disable blending: an exact opaque path must not borrow foreign OM state.
    Microsoft::WRL::ComPtr<ID3D11BlendState> liveBlend;
    UINT sampleMask = 0;
    context->OMGetBlendState(liveBlend.GetAddressOf(), nullptr, &sampleMask);
    return !liveBlend && sampleMask == D3D11_DEFAULT_SAMPLE_MASK;
}
} // namespace outrun::vr::dx11
