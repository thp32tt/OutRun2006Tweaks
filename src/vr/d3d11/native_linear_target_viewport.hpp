#pragma once
// R199: dormant non-indexed D3D11 Draw full target and viewport ownership.
// This preflight never dispatches a gameplay Draw; WARP GPU proof is tool-only.
#include "native_linear_draw_submit.hpp"

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_linear_full_target_draw_ready(
    const NativeLinearBufferMirror& vb, ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount,
    std::uint64_t generation, std::uint64_t vertexSnapshotVersion,
    UINT width, UINT height, DXGI_FORMAT format,
    ID3D11RenderTargetView* expectedTarget) noexcept {
    if (!width || !height || !expectedTarget ||
        format == DXGI_FORMAT_UNKNOWN ||
        !verified_linear_draw_ready(
            vb, context, startVertex, vertexCount,
            generation, vertexSnapshotVersion))
        return false;

    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> liveTarget;
    context->OMGetRenderTargets(1, liveTarget.GetAddressOf(), nullptr);
    // A foreign eye's valid, identically sized RTV must not be accepted.
    if (!liveTarget || liveTarget.Get() != expectedTarget) return false;

    D3D11_RENDER_TARGET_VIEW_DESC view{};
    liveTarget->GetDesc(&view);
    if (view.ViewDimension != D3D11_RTV_DIMENSION_TEXTURE2D ||
        view.Texture2D.MipSlice != 0 || view.Format != format)
        return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> resource;
    liveTarget->GetResource(resource.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> color;
    if (!resource || FAILED(resource.As(&color)) || !color)
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    color->GetDesc(&desc);
    if (desc.Width != width || desc.Height != height ||
        desc.MipLevels != 1 || desc.ArraySize != 1 ||
        desc.SampleDesc.Count != 1 || desc.SampleDesc.Quality != 0 ||
        desc.Format != format ||
        !(desc.BindFlags & D3D11_BIND_RENDER_TARGET))
        return false;

    // RSGetViewports with capacity one does not prove there isn't another
    // stale eye viewport. Query the full count before asking for the value.
    UINT boundCount = 0;
    context->RSGetViewports(&boundCount, nullptr);
    if (boundCount != 1) return false;
    D3D11_VIEWPORT viewport{};
    boundCount = 1;
    context->RSGetViewports(&boundCount, &viewport);
    if (boundCount != 1 ||
        !(viewport.TopLeftX == 0.f) || !(viewport.TopLeftY == 0.f) ||
        !(viewport.Width == static_cast<float>(width)) ||
        !(viewport.Height == static_cast<float>(height)) ||
        !(viewport.MinDepth == 0.f) || !(viewport.MaxDepth == 1.f))
        return false;

    // A retained scissor could eliminate otherwise valid geometry.
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
