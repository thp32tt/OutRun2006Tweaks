#pragma once
// R193: dormant owned native indexed scissor/RTV preflight.
// The protected R187 path continues to reject scissor; no gameplay Draw is dispatched.
#include "native_indexed_draw_submit.hpp"
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_indexed_scissor_draw_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    ID3D11DeviceContext* context, UINT startIndex, UINT indexCount, INT baseVertex,
    std::uint64_t generation, std::uint64_t vbVersion, std::uint64_t ibVersion,
    UINT width, UINT height, DXGI_FORMAT format,
    ID3D11RenderTargetView* expectedRtv, ID3D11RasterizerState* expectedRaster,
    const D3D11_RECT& expectedRect) noexcept {
    if (!context || !expectedRtv || !expectedRaster ||
        !width || !height || width > 0x7fffffffU || height > 0x7fffffffU ||
        format == DXGI_FORMAT_UNKNOWN ||
        expectedRect.left < 0 || expectedRect.top < 0 ||
        expectedRect.right <= expectedRect.left ||
        expectedRect.bottom <= expectedRect.top ||
        expectedRect.right > static_cast<LONG>(width) ||
        expectedRect.bottom > static_cast<LONG>(height) ||
        !verified_indexed_linear_draw_ready(vb, ib, context, startIndex,
            indexCount, baseVertex, generation, vbVersion, ibVersion))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> device, rasterOwner;
    context->GetDevice(device.GetAddressOf());
    expectedRaster->GetDevice(rasterOwner.GetAddressOf());
    if (!device || rasterOwner.Get() != device.Get()) return false;

    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> liveTarget;
    context->OMGetRenderTargets(1, liveTarget.GetAddressOf(), nullptr);
    if (liveTarget.Get() != expectedRtv) return false;
    D3D11_RENDER_TARGET_VIEW_DESC view{};
    expectedRtv->GetDesc(&view);
    if (view.ViewDimension != D3D11_RTV_DIMENSION_TEXTURE2D ||
        view.Texture2D.MipSlice != 0 || view.Format != format)
        return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> resource;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> color;
    expectedRtv->GetResource(resource.GetAddressOf());
    if (!resource || FAILED(resource.As(&color)) || !color) return false;
    D3D11_TEXTURE2D_DESC tex{};
    color->GetDesc(&tex);
    if (tex.Width != width || tex.Height != height || tex.MipLevels != 1 ||
        tex.ArraySize != 1 || tex.Format != format ||
        tex.SampleDesc.Count != 1 || tex.SampleDesc.Quality != 0 ||
        !(tex.BindFlags & D3D11_BIND_RENDER_TARGET))
        return false;

    UINT viewportCount = 0;
    context->RSGetViewports(&viewportCount, nullptr);
    if (viewportCount != 1) return false;
    D3D11_VIEWPORT vp{};
    viewportCount = 1;
    context->RSGetViewports(&viewportCount, &vp);
    if (viewportCount != 1 || vp.TopLeftX != 0.f || vp.TopLeftY != 0.f ||
        vp.Width != static_cast<float>(width) ||
        vp.Height != static_cast<float>(height) ||
        vp.MinDepth != 0.f || vp.MaxDepth != 1.f)
        return false;

    Microsoft::WRL::ComPtr<ID3D11RasterizerState> liveRaster;
    context->RSGetState(liveRaster.GetAddressOf());
    if (liveRaster.Get() != expectedRaster) return false;
    D3D11_RASTERIZER_DESC desc{};
    expectedRaster->GetDesc(&desc);
    if (!desc.ScissorEnable || desc.FillMode != D3D11_FILL_SOLID ||
        desc.CullMode != D3D11_CULL_NONE || !desc.DepthClipEnable)
        return false;

    // Request count first: a single requested rect would hide stale extra eye clips.
    UINT rectCount = 0;
    context->RSGetScissorRects(&rectCount, nullptr);
    if (rectCount != 1) return false;
    D3D11_RECT liveRect{};
    rectCount = 1;
    context->RSGetScissorRects(&rectCount, &liveRect);
    return rectCount == 1 &&
        liveRect.left == expectedRect.left && liveRect.top == expectedRect.top &&
        liveRect.right == expectedRect.right &&
        liveRect.bottom == expectedRect.bottom;
}
} // namespace outrun::vr::dx11
