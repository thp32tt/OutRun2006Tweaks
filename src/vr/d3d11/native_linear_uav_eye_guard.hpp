#pragma once
// R221: dormant non-indexed Draw rejects hidden OM UAV side-eye outputs.
// R216 already owns D32 depth/RTV/RS; it does not enumerate OM UAV state.
#include "native_linear_target_viewport.hpp"

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_linear_uav_isolated_eye_ready(
    const NativeLinearBufferMirror& vb, ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount,
    std::uint64_t generation, std::uint64_t snapshotVersion,
    UINT width, UINT height, DXGI_FORMAT format,
    ID3D11InputLayout* expectedLayout,
    ID3D11VertexShader* expectedVs, ID3D11PixelShader* expectedPs,
    ID3D11RenderTargetView* expectedRtv,
    ID3D11DepthStencilView* expectedDsv,
    ID3D11DepthStencilState* expectedDepthState,
    ID3D11RasterizerState* expectedRaster) noexcept {
    if (!context || !expectedRtv || !expectedDsv ||
        !verified_linear_float_depth_eye_draw_ready(
            vb, context, startVertex, vertexCount, generation,
            snapshotVersion, width, height, format, expectedLayout,
            expectedVs, expectedPs, expectedRtv, expectedDsv,
            expectedDepthState, expectedRaster))
        return false;
    ID3D11RenderTargetView* liveRtv = nullptr;
    ID3D11DepthStencilView* liveDsv = nullptr;
    ID3D11UnorderedAccessView* uavs[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    context->OMGetRenderTargetsAndUnorderedAccessViews(
        1u, &liveRtv, &liveDsv, 0u, D3D11_PS_CS_UAV_REGISTER_COUNT, uavs);
    bool isolated = liveRtv == expectedRtv && liveDsv == expectedDsv;
    // OMGet increments every returned COM reference, even if preflight fails.
    if (liveRtv) liveRtv->Release();
    if (liveDsv) liveDsv->Release();
    for (auto* uav : uavs) {
        if (uav) {
            isolated = false;
            uav->Release();
        }
    }
    return isolated;
}
} // namespace outrun::vr::dx11
