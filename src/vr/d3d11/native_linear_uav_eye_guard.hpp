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


// R230: a live D3D11 predicate can suppress an otherwise owned, sole-eye
// non-indexed Draw. Both polarities are unproven; never activate game Draw.
[[nodiscard]] inline bool verified_linear_unpredicated_eye_ready(
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
    if (!context || !verified_linear_uav_isolated_eye_ready(
            vb, context, startVertex, vertexCount,
            generation, snapshotVersion, width, height, format,
            expectedLayout, expectedVs, expectedPs, expectedRtv,
            expectedDsv, expectedDepthState, expectedRaster))
        return false;
    Microsoft::WRL::ComPtr<ID3D11Predicate> livePredicate;
    BOOL predicatePolarity = FALSE;
    context->GetPredication(livePredicate.GetAddressOf(), &predicatePolarity);
    return !livePredicate;
}

// R232: even an otherwise unpredicated, sole-eye non-indexed Draw can retain
// a stream-output destination invisible to OM/UAV checks. Reject all SO slots
// before ever considering native gameplay activation; no Draw dispatch here.
[[nodiscard]] inline bool verified_linear_no_stream_output_eye_ready(
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
    if (!context || !verified_linear_unpredicated_eye_ready(
            vb, context, startVertex, vertexCount,
            generation, snapshotVersion, width, height, format,
            expectedLayout, expectedVs, expectedPs, expectedRtv,
            expectedDsv, expectedDepthState, expectedRaster))
        return false;
    ID3D11Buffer* soTargets[D3D11_SO_BUFFER_SLOT_COUNT]{};
    context->SOGetTargets(D3D11_SO_BUFFER_SLOT_COUNT, soTargets);
    bool isolated = true;
    // SOGetTargets AddRefs each returned target, including rejected slots.
    for (auto* target : soTargets) {
        if (target) {
            isolated = false;
            target->Release();
        }
    }
    return isolated;
}

} // namespace outrun::vr::dx11
