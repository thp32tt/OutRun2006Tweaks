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
    // R224: RTV.Format alone does not seal a TYPELESS underlying texture.
    // A native eye's exact color ownership requires a dedicated typed
    // DEFAULT allocation without CPU access or alias-enabling misc flags.
    if (desc.Width != width || desc.Height != height ||
        desc.MipLevels != 1 || desc.ArraySize != 1 ||
        desc.SampleDesc.Count != 1 || desc.SampleDesc.Quality != 0 ||
        desc.Format != format || desc.Usage != D3D11_USAGE_DEFAULT ||
        desc.CPUAccessFlags != 0 || desc.MiscFlags != 0 ||
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
// R215: compose the previously independent full-target/viewport (R199),
// depth + single-eye + opaque OM (R214), and exact raster ownership into one
// dormant non-indexed eye preflight. Passing R214 alone did not attest that
// the eye viewport was full-sized or that RS belonged to the intended owner.
// No gameplay Draw is authorized or submitted by this helper.
[[nodiscard]] inline bool verified_linear_sealed_opaque_eye_draw_ready(
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
    if (!context || !expectedRaster ||
        !verified_linear_full_target_draw_ready(
            vb, context, startVertex, vertexCount, generation,
            snapshotVersion, width, height, format, expectedRtv) ||
        !verified_linear_opaque_single_eye_draw_ready(
            vb, context, startVertex, vertexCount, generation,
            snapshotVersion, expectedLayout, expectedVs, expectedPs,
            expectedRtv, expectedDsv, expectedDepthState))
        return false;

    // R215 depth surface: an exact DSV object may still target mip 1 of
    // a larger texture. Seal the *resource* as a dedicated full-eye surface,
    // not just a compatible view with a matching OM object identity.
    D3D11_DEPTH_STENCIL_VIEW_DESC depthView{};
    expectedDsv->GetDesc(&depthView);
    if (depthView.ViewDimension != D3D11_DSV_DIMENSION_TEXTURE2D ||
        depthView.Texture2D.MipSlice != 0) return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> depthResource;
    expectedDsv->GetResource(depthResource.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> depthTexture;
    if (!depthResource || FAILED(depthResource.As(&depthTexture)) ||
        !depthTexture) return false;
    D3D11_TEXTURE2D_DESC depthDesc{};
    depthTexture->GetDesc(&depthDesc);
    if (depthDesc.Width != width || depthDesc.Height != height ||
        depthDesc.MipLevels != 1 || depthDesc.ArraySize != 1 ||
        depthDesc.SampleDesc.Count != 1 ||
        depthDesc.SampleDesc.Quality != 0 ||
        !(depthDesc.BindFlags & D3D11_BIND_DEPTH_STENCIL)) return false;

    Microsoft::WRL::ComPtr<ID3D11RasterizerState> liveRaster;
    context->RSGetState(liveRaster.GetAddressOf());
    if (liveRaster.Get() != expectedRaster) return false;
    Microsoft::WRL::ComPtr<ID3D11Device> liveDevice, rasterDevice;
    context->GetDevice(liveDevice.GetAddressOf());
    expectedRaster->GetDevice(rasterDevice.GetAddressOf());
    if (!liveDevice || rasterDevice.Get() != liveDevice.Get()) return false;
    D3D11_RASTERIZER_DESC desc{};
    expectedRaster->GetDesc(&desc);
    // This deliberately narrow path proves the existing WARP triangle with
    // CULL_NONE; explicit culling has a separately owned R201 contract.
    return desc.FillMode == D3D11_FILL_SOLID &&
        desc.CullMode == D3D11_CULL_NONE &&
        !desc.ScissorEnable && desc.DepthClipEnable &&
        desc.DepthBias == 0 && desc.DepthBiasClamp == 0.f &&
        desc.SlopeScaledDepthBias == 0.f &&
        !desc.MultisampleEnable && !desc.AntialiasedLineEnable;
}


// R216: separate precision/readonly-owner fence for the dormant WARP eye.
// R215 proves geometry/OM/RS identity but intentionally admits e.g. D16
// depth. Only an explicitly typed, writable, dedicated D32_FLOAT texture
// may be called an exact 32-bit float-depth eye. No gameplay Draw occurs.
[[nodiscard]] inline bool verified_linear_float_depth_eye_draw_ready(
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
    if (!expectedDsv ||
        !verified_linear_sealed_opaque_eye_draw_ready(
            vb, context, startVertex, vertexCount, generation,
            snapshotVersion, width, height, format, expectedLayout,
            expectedVs, expectedPs, expectedRtv, expectedDsv,
            expectedDepthState, expectedRaster))
        return false;

    D3D11_DEPTH_STENCIL_VIEW_DESC view{};
    expectedDsv->GetDesc(&view);
    if (view.Format != DXGI_FORMAT_D32_FLOAT || view.Flags != 0)
        return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> resource;
    expectedDsv->GetResource(resource.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> depthTexture;
    if (!resource || FAILED(resource.As(&depthTexture)) || !depthTexture)
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    depthTexture->GetDesc(&desc);
    return desc.Format == DXGI_FORMAT_D32_FLOAT &&
        desc.Usage == D3D11_USAGE_DEFAULT && desc.CPUAccessFlags == 0;
}

} // namespace outrun::vr::dx11
