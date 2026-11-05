#pragma once
// R219: isolated native indexed eye rejects hidden OM UAV side outputs.
// R218 seals RTV/DSV/depth/raster, but an OM UAV can still write a second
// texture during the same DrawIndexed without occupying any RTV slot.
// Dormant readiness only: no game DrawIndexed dispatch or backend activation.
#include "native_indexed_target_viewport.hpp"

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_indexed_uav_isolated_eye_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    ID3D11DeviceContext* context, UINT firstIndex, UINT indexCount,
    INT baseVertex, std::uint64_t generation, std::uint64_t vbVersion,
    std::uint64_t ibVersion, UINT width, UINT height, DXGI_FORMAT format,
    ID3D11InputLayout* expectedLayout,
    ID3D11VertexShader* expectedVs, ID3D11PixelShader* expectedPs,
    ID3D11RenderTargetView* expectedRtv,
    ID3D11DepthStencilView* expectedDsv,
    ID3D11DepthStencilState* expectedDepthState,
    ID3D11RasterizerState* expectedRaster) noexcept {
    if (!context || !expectedRtv || !expectedDsv ||
        !verified_indexed_sealed_opaque_eye_draw_ready(
            vb, ib, context, firstIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion, width, height, format,
            expectedLayout, expectedVs, expectedPs, expectedRtv,
            expectedDsv, expectedDepthState, expectedRaster))
        return false;

    // OMGetRenderTargets alone hides pixel-shader UAV outputs. Inspect all
    // D3D11.0 OM UAV slots, including slots not referenced by the expected PS.
    ID3D11RenderTargetView* liveRtv[1]{};
    ID3D11DepthStencilView* liveDsv = nullptr;
    ID3D11UnorderedAccessView* liveUavs[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    context->OMGetRenderTargetsAndUnorderedAccessViews(
        1u, liveRtv, &liveDsv, 0u, D3D11_PS_CS_UAV_REGISTER_COUNT, liveUavs);
    bool isolated = liveRtv[0] == expectedRtv && liveDsv == expectedDsv;
    // Every returned pointer owns one COM ref, even on fail-closed paths.
    if (liveRtv[0]) liveRtv[0]->Release();
    if (liveDsv) liveDsv->Release();
    for (auto* uav : liveUavs) {
        if (uav) {
            isolated = false;
            uav->Release();
        }
    }
    return isolated;
}

// R229: R219 proves sole-eye OM ownership, but a live GPU predicate can
// silently skip this otherwise owned DrawIndexed. No game draw dispatch here.
[[nodiscard]] inline bool verified_indexed_unpredicated_eye_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    ID3D11DeviceContext* context, UINT firstIndex, UINT indexCount,
    INT baseVertex, std::uint64_t generation, std::uint64_t vbVersion,
    std::uint64_t ibVersion, UINT width, UINT height, DXGI_FORMAT format,
    ID3D11InputLayout* expectedLayout,
    ID3D11VertexShader* expectedVs, ID3D11PixelShader* expectedPs,
    ID3D11RenderTargetView* expectedRtv, ID3D11DepthStencilView* expectedDsv,
    ID3D11DepthStencilState* expectedDepthState,
    ID3D11RasterizerState* expectedRaster) noexcept {
    if (!context || !verified_indexed_uav_isolated_eye_ready(
            vb, ib, context, firstIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion, width, height, format,
            expectedLayout, expectedVs, expectedPs, expectedRtv,
            expectedDsv, expectedDepthState, expectedRaster))
        return false;
    Microsoft::WRL::ComPtr<ID3D11Predicate> livePredicate;
    BOOL predicatePolarity = FALSE;
    context->GetPredication(livePredicate.GetAddressOf(), &predicatePolarity);
    // Both polarities can suppress a native draw until a query-result
    // ownership contract is implemented. Do not assume a stale result.
    return !livePredicate;
}

 
// R231: a retained stream-output buffer is a hidden GPU write destination
// even when the selected indexed RTV/DSV/UAVs and predication are clean.
// Refuse the dormant DrawIndexed path until every SO slot is unbound.
// SOGetTargets AddRefs each returned buffer; release even on rejection.
[[nodiscard]] inline bool verified_indexed_no_stream_output_eye_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    ID3D11DeviceContext* context, UINT firstIndex, UINT indexCount,
    INT baseVertex, std::uint64_t generation, std::uint64_t vbVersion,
    std::uint64_t ibVersion, UINT width, UINT height, DXGI_FORMAT format,
    ID3D11InputLayout* expectedLayout,
    ID3D11VertexShader* expectedVs, ID3D11PixelShader* expectedPs,
    ID3D11RenderTargetView* expectedRtv, ID3D11DepthStencilView* expectedDsv,
    ID3D11DepthStencilState* expectedDepthState,
    ID3D11RasterizerState* expectedRaster) noexcept {
    if (!context || !verified_indexed_unpredicated_eye_ready(
            vb, ib, context, firstIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion, width, height, format,
            expectedLayout, expectedVs, expectedPs, expectedRtv,
            expectedDsv, expectedDepthState, expectedRaster))
        return false;
    ID3D11Buffer* soTargets[D3D11_SO_BUFFER_SLOT_COUNT]{};
    context->SOGetTargets(D3D11_SO_BUFFER_SLOT_COUNT, soTargets);
    bool isolated = true;
    for (auto* target : soTargets) {
        if (target) {
            isolated = false;
            target->Release();
        }
    }
    return isolated;
}

} // namespace outrun::vr::dx11
