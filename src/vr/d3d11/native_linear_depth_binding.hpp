#pragma once
// R202: dormant native non-indexed Draw owns exact live DSV/depth-state binding.
// WARP GPU proof is isolated to tools; no game-native Draw is dispatched.
#include "native_linear_target_viewport.hpp"
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_linear_depth_draw_ready(
    const NativeLinearBufferMirror& vb, ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount,
    std::uint64_t generation, std::uint64_t vbVersion,
    UINT targetWidth, UINT targetHeight, DXGI_FORMAT targetFormat,
    ID3D11RenderTargetView* expectedRtv, ID3D11DepthStencilView* expectedDsv,
    ID3D11DepthStencilState* expectedDepthState) noexcept {
    if (!expectedDsv || !expectedDepthState ||
        !verified_linear_full_target_draw_ready(
            vb, context, startVertex, vertexCount, generation, vbVersion,
            targetWidth, targetHeight, targetFormat, expectedRtv))
        return false;

    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> liveRtv;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilView> liveDsv;
    context->OMGetRenderTargets(1, liveRtv.GetAddressOf(), liveDsv.GetAddressOf());
    // Reject same-size but stale eye DSV and a rebound RTV before Draw.
    if (liveRtv.Get() != expectedRtv || liveDsv.Get() != expectedDsv)
        return false;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilState> liveDepthState;
    UINT stencilRef = 0;
    context->OMGetDepthStencilState(liveDepthState.GetAddressOf(), &stencilRef);
    if (liveDepthState.Get() != expectedDepthState || stencilRef != 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> device, depthDevice, stateDevice;
    context->GetDevice(device.GetAddressOf());
    expectedDsv->GetDevice(depthDevice.GetAddressOf());
    expectedDepthState->GetDevice(stateDevice.GetAddressOf());
    if (!device || depthDevice.Get() != device.Get() ||
        stateDevice.Get() != device.Get())
        return false;
    D3D11_DEPTH_STENCIL_VIEW_DESC view{};
    expectedDsv->GetDesc(&view);
    if (view.ViewDimension != D3D11_DSV_DIMENSION_TEXTURE2D ||
        view.Texture2D.MipSlice != 0 ||
        view.Format != DXGI_FORMAT_D24_UNORM_S8_UINT ||
        view.Flags != 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Resource> depthResource, colorResource;
    expectedDsv->GetResource(depthResource.GetAddressOf());
    expectedRtv->GetResource(colorResource.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> depth;
    if (!depthResource || !colorResource ||
        depthResource.Get() == colorResource.Get() ||
        FAILED(depthResource.As(&depth)) || !depth)
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    depth->GetDesc(&desc);
    if (desc.Width != targetWidth || desc.Height != targetHeight ||
        desc.MipLevels != 1 || desc.ArraySize != 1 ||
        desc.SampleDesc.Count != 1 || desc.SampleDesc.Quality != 0 ||
        desc.Format != DXGI_FORMAT_D24_UNORM_S8_UINT ||
        !(desc.BindFlags & D3D11_BIND_DEPTH_STENCIL))
        return false;

    D3D11_DEPTH_STENCIL_DESC ds{};
    expectedDepthState->GetDesc(&ds);
    if (!ds.DepthEnable || ds.DepthWriteMask != D3D11_DEPTH_WRITE_MASK_ALL ||
        ds.DepthFunc != D3D11_COMPARISON_LESS || ds.StencilEnable)
        return false;

    Microsoft::WRL::ComPtr<ID3D11RasterizerState> rs;
    context->RSGetState(rs.GetAddressOf());
    if (rs) {
        D3D11_RASTERIZER_DESC raster{};
        rs->GetDesc(&raster);
        if (!raster.DepthClipEnable) return false;
    }
    return true;
}
} // namespace outrun::vr::dx11
