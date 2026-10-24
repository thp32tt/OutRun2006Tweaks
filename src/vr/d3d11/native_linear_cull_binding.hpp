#pragma once
// R201: fail-closed native non-indexed Draw exact raster cull/winding ownership.
// Tool-only WARP Draw verifies pixels. Gameplay native Draw remains dormant.
#include "native_linear_target_viewport.hpp"
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_linear_cull_draw_ready(
    const NativeLinearBufferMirror& vb, ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount, std::uint64_t generation,
    std::uint64_t vbVersion, UINT width, UINT height,
    DXGI_FORMAT format, ID3D11RenderTargetView* expectedRtv,
    ID3D11RasterizerState* expectedRaster,
    D3D11_CULL_MODE expectedCull, bool expectedFrontCCW) noexcept {
    if (!expectedRaster ||
        (expectedCull != D3D11_CULL_FRONT && expectedCull != D3D11_CULL_BACK) ||
        !verified_linear_full_target_draw_ready(
            vb, context, startVertex, vertexCount, generation, vbVersion,
            width, height, format, expectedRtv))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> device, rasterDevice;
    context->GetDevice(device.GetAddressOf());
    expectedRaster->GetDevice(rasterDevice.GetAddressOf());
    if (!device || rasterDevice.Get() != device.Get())
        return false;

    Microsoft::WRL::ComPtr<ID3D11RasterizerState> liveRaster;
    context->RSGetState(liveRaster.GetAddressOf());
    if (liveRaster.Get() != expectedRaster) return false;
    D3D11_RASTERIZER_DESC desc{};
    expectedRaster->GetDesc(&desc);
    // A source-owned D3D9 triangle must not silently inherit fill, bias,
    // scissor, AA or winding from a previous native draw in the other eye.
    return desc.FillMode == D3D11_FILL_SOLID &&
        desc.CullMode == expectedCull &&
        desc.FrontCounterClockwise == (expectedFrontCCW ? TRUE : FALSE) &&
        !desc.ScissorEnable && desc.DepthClipEnable &&
        desc.DepthBias == 0 && desc.DepthBiasClamp == 0.f &&
        desc.SlopeScaledDepthBias == 0.f &&
        !desc.MultisampleEnable && !desc.AntialiasedLineEnable;
}
} // namespace outrun::vr::dx11
