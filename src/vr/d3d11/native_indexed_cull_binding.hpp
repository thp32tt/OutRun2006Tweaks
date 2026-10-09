#pragma once
// R194: dormant indexed native raster front-face/cull ownership preflight.
// No game draw activation: only tools/dx11_cull_indexed_probe_r194.cpp dispatches.
#include "native_indexed_target_viewport.hpp"
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_indexed_cull_draw_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    ID3D11DeviceContext* context, UINT startIndex, UINT indexCount, INT baseVertex,
    std::uint64_t generation, std::uint64_t vbVersion, std::uint64_t ibVersion,
    UINT targetWidth, UINT targetHeight, DXGI_FORMAT targetFormat,
    ID3D11RenderTargetView* expectedRtv, ID3D11RasterizerState* expectedRaster,
    D3D11_CULL_MODE expectedCull, bool expectedFrontCCW) noexcept {
    if (!expectedRaster ||
        (expectedCull != D3D11_CULL_FRONT && expectedCull != D3D11_CULL_BACK) ||
        !verified_indexed_full_target_draw_ready(
            vb, ib, context, startIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion, targetWidth, targetHeight,
            targetFormat, expectedRtv))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> device, rasterOwner;
    context->GetDevice(device.GetAddressOf());
    expectedRaster->GetDevice(rasterOwner.GetAddressOf());
    if (!device || rasterOwner.Get() != device.Get()) return false;

    Microsoft::WRL::ComPtr<ID3D11RasterizerState> liveRaster;
    context->RSGetState(liveRaster.GetAddressOf());
    if (liveRaster.Get() != expectedRaster) return false;
    D3D11_RASTERIZER_DESC raster{};
    expectedRaster->GetDesc(&raster);
    return raster.FillMode == D3D11_FILL_SOLID &&
        raster.CullMode == expectedCull &&
        raster.FrontCounterClockwise == (expectedFrontCCW ? TRUE : FALSE) &&
        !raster.ScissorEnable && raster.DepthClipEnable &&
        raster.DepthBias == 0 && raster.DepthBiasClamp == 0.f &&
        raster.SlopeScaledDepthBias == 0.f &&
        !raster.MultisampleEnable && !raster.AntialiasedLineEnable;
}
} // namespace outrun::vr::dx11
