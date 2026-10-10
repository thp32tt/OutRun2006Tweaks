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
    DXGI_FORMAT format, ID3D11RenderTargetView* expectedTarget,
    ID3D11DepthStencilView* expectedDepthTarget = nullptr) noexcept {
    if (!width || !height || !expectedTarget ||
        format == DXGI_FORMAT_UNKNOWN ||
        !verified_indexed_linear_draw_ready(
            vb, ib, context, startIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion))
        return false;

    // An indexed eye draw must not broadcast pixels to a stale second-eye
    // RTV. OMGetRenderTargets(1) cannot reveal extra bound MRT slots.
    ID3D11RenderTargetView* outputs[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT] = {};
    // R205 E002: unowned DSV is forbidden; a depth-enabled caller must pass
    // an exact expected DSV, then verify depth state/resource through R189.
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
    if (unownedDepth.Get() != expectedDepthTarget || hasExtraOutput ||
        !target || target.Get() != expectedTarget)
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

// R218: composed indexed full-eye D32 readiness: R187 seals full RTV/viewport,
// R217 seals indexed IA/shader/depth/opaque OM; neither seals dedicated DSV
// subresource nor exact raster ownership. No production DrawIndexed dispatch.
[[nodiscard]] inline bool verified_indexed_sealed_opaque_eye_draw_ready(
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
    if (!context || !expectedDsv || !expectedRaster ||
        !verified_indexed_full_target_draw_ready(
            vb, ib, context, firstIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion, width, height, format,
            expectedRtv, expectedDsv) ||
        !verified_indexed_opaque_depth_single_eye_ready(
            vb, ib, context, firstIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion,
            expectedLayout, expectedVs, expectedPs, expectedRtv,
            expectedDsv, expectedDepthState))
        return false;
    D3D11_DEPTH_STENCIL_VIEW_DESC depthView{};
    expectedDsv->GetDesc(&depthView);
    if (depthView.ViewDimension != D3D11_DSV_DIMENSION_TEXTURE2D ||
        depthView.Texture2D.MipSlice != 0 ||
        depthView.Format != DXGI_FORMAT_D32_FLOAT ||
        depthView.Flags != 0) return false;
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
        depthDesc.Format != DXGI_FORMAT_D32_FLOAT ||
        depthDesc.Usage != D3D11_USAGE_DEFAULT ||
        depthDesc.CPUAccessFlags != 0 ||
        !(depthDesc.BindFlags & D3D11_BIND_DEPTH_STENCIL))
        return false;
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> liveRaster;
    context->RSGetState(liveRaster.GetAddressOf());
    if (liveRaster.Get() != expectedRaster) return false;
    Microsoft::WRL::ComPtr<ID3D11Device> liveDevice, rasterDevice;
    context->GetDevice(liveDevice.GetAddressOf());
    expectedRaster->GetDevice(rasterDevice.GetAddressOf());
    if (!liveDevice || liveDevice.Get() != rasterDevice.Get()) return false;
    D3D11_RASTERIZER_DESC rasterDesc{};
    expectedRaster->GetDesc(&rasterDesc);
    return rasterDesc.FillMode == D3D11_FILL_SOLID &&
        rasterDesc.CullMode == D3D11_CULL_NONE &&
        !rasterDesc.ScissorEnable && rasterDesc.DepthClipEnable &&
        rasterDesc.DepthBias == 0 && rasterDesc.DepthBiasClamp == 0.f &&
        rasterDesc.SlopeScaledDepthBias == 0.f &&
        !rasterDesc.MultisampleEnable && !rasterDesc.AntialiasedLineEnable;
}
} // namespace outrun::vr::dx11
