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
    // R196: D3D9 FVF triangle-list translation has no GS/HS/DS stage.
    // Unexpected retained shader stages can rewrite/discard geometry even
    // when VS/PS and owned IA objects match. Fail closed before any Draw.
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

 
// R207: stronger, opt-in object provenance for a *specific* indexed pipeline.
// R186 checks same-device ownership but cannot distinguish a different shader
// or render target created by that very same device. A native caller must
// supply all four exact expected objects before treating a snapshot as ready.
// No gameplay DrawIndexed dispatch or backend activation is performed here.
[[nodiscard]] inline bool verified_indexed_pipeline_identity_ready(
    const NativeLinearBufferMirror& vertexOwner,
    const NativeLinearBufferMirror& indexOwner,
    ID3D11DeviceContext* context,
    UINT startIndex, UINT indexCount, INT baseVertexLocation,
    std::uint64_t deviceGeneration,
    std::uint64_t vertexSnapshotVersion,
    std::uint64_t indexSnapshotVersion,
    ID3D11InputLayout* expectedLayout,
    ID3D11VertexShader* expectedVs,
    ID3D11PixelShader* expectedPs,
    ID3D11RenderTargetView* expectedRtv) noexcept {
    if (!expectedLayout || !expectedVs || !expectedPs || !expectedRtv ||
        !verified_indexed_linear_draw_ready(
            vertexOwner, indexOwner, context, startIndex, indexCount,
            baseVertexLocation, deviceGeneration, vertexSnapshotVersion,
            indexSnapshotVersion))
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


// R212: indexed DrawIndexed exact OM eye ownership, independent of R211.
// R207 checks RTV0 only; a live SV_Target1 can write a secondary eye.
// Dormant/readiness-only: never activate gameplay DrawIndexed here.
[[nodiscard]] inline bool verified_indexed_single_eye_output_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    ID3D11DeviceContext* context, UINT firstIndex, UINT indexCount,
    INT baseVertex, std::uint64_t gen, std::uint64_t vbVer,
    std::uint64_t ibVer, ID3D11InputLayout* layout,
    ID3D11VertexShader* vs, ID3D11PixelShader* ps,
    ID3D11RenderTargetView* expectedRtv) noexcept {
    if (!context || !expectedRtv ||
        !verified_indexed_pipeline_identity_ready(
            vb,ib,context,firstIndex,indexCount,baseVertex,
            gen,vbVer,ibVer,layout,vs,ps,expectedRtv))
        return false;
    ID3D11RenderTargetView* views[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]{};
    context->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
                                views,nullptr);
    bool single = views[0] == expectedRtv;
    for (UINT i=1; i<D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++i)
        if (views[i]) single=false;
    // OMGetRenderTargets AddRef: balance every returned COM reference.
    for (auto* v: views)
        if (v) v->Release();
    return single;
}
} // namespace outrun::vr::dx11
