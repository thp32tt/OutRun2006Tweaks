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
} // namespace outrun::vr::dx11
