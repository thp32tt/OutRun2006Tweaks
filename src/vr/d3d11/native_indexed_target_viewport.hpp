#pragma once
// R187: dormant indexed native Draw target/viewport ownership preflight.
// This cannot activate a game Draw; the only GPU dispatch is in the isolated WARP probe.
#include "native_indexed_draw_submit.hpp"

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_indexed_full_target_draw_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    ID3D11DeviceContext* context, UINT startIndex, UINT indexCount,
    INT baseVertex, std::uint64_t generation, std::uint64_t vbVersion,
    std::uint64_t ibVersion, UINT width, UINT height,
    DXGI_FORMAT format, ID3D11RenderTargetView* expectedTarget) noexcept {
    if (!width || !height || !expectedTarget ||
        format == DXGI_FORMAT_UNKNOWN ||
        !verified_indexed_linear_draw_ready(
            vb, ib, context, startIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion))
        return false;

    // An indexed eye draw must not broadcast pixels to a stale second-eye
    // RTV. OMGetRenderTargets(1) cannot reveal extra bound MRT slots.
    ID3D11RenderTargetView* outputs[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT] = {};
    // R205: this color-only indexed path cannot inherit an unowned DSV.
    // Depth-enabled indexed draws use the independently validated R189 path.
    Microsoft::WRL::ComPtr<ID3D11DepthStencilView> unownedDepth;
    context->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
        outputs, unownedDepth.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> target;
    target.Attach(outputs[0]); // Adopt the reference returned by OMGetRenderTargets.
    bool hasExtraOutput = false;
    for (UINT slot = 1; slot < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++slot) {
        if (outputs[slot]) {
            hasExtraOutput = true;
            outputs[slot]->Release(); // Query added one reference per occupied slot.
        }
    }
    // Equal-sized eye targets are not interchangeable: require a sole owned RTV.
    if (unownedDepth || hasExtraOutput || !target || target.Get() != expectedTarget)
        return false;
    D3D11_RENDER_TARGET_VIEW_DESC view{};
    target->GetDesc(&view);
    if (view.ViewDimension != D3D11_RTV_DIMENSION_TEXTURE2D ||
        view.Texture2D.MipSlice != 0 || view.Format != format)
        return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> resource;
    target->GetResource(resource.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> color;
    if (!resource || FAILED(resource.As(&color)) || !color)
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    color->GetDesc(&desc);
    if (desc.Width != width || desc.Height != height ||
        desc.MipLevels != 1 || desc.ArraySize != 1 ||
        desc.SampleDesc.Count != 1 || desc.SampleDesc.Quality != 0 ||
        desc.Format != format || !(desc.BindFlags & D3D11_BIND_RENDER_TARGET))
        return false;

    // Query the actual bound count first; requesting one viewport alone
    // would miss stale second-eye viewports.
    UINT boundCount = 0;
    context->RSGetViewports(&boundCount, nullptr);
    if (boundCount != 1) return false;
    D3D11_VIEWPORT vp{};
    boundCount = 1;
    context->RSGetViewports(&boundCount, &vp);
    if (boundCount != 1 || !(vp.TopLeftX == 0.f) ||
        !(vp.TopLeftY == 0.f) ||
        !(vp.Width == static_cast<float>(width)) ||
        !(vp.Height == static_cast<float>(height)) ||
        !(vp.MinDepth == 0.f) || !(vp.MaxDepth == 1.f))
        return false;

    // A hidden scissor can clip an apparently valid native draw.
    // Until exact scissor provenance is implemented, reject scissor-enabled state.
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> raster;
    context->RSGetState(raster.GetAddressOf());
    if (raster) {
        D3D11_RASTERIZER_DESC rasterDesc{};
        raster->GetDesc(&rasterDesc);
        if (rasterDesc.ScissorEnable) return false;
    }
    return true;
}
} // namespace outrun::vr::dx11
