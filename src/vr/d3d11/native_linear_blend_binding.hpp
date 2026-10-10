#pragma once
// R200: dormant native non-indexed Draw exact live OM alpha-blend ownership.
// Never activates gameplay Draw; actual pixels are validated in isolated WARP.
#include "native_linear_target_viewport.hpp"
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_linear_blend_draw_ready(
    const NativeLinearBufferMirror& vb, ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount, std::uint64_t generation,
    std::uint64_t vbVersion, UINT targetWidth, UINT targetHeight,
    DXGI_FORMAT targetFormat, ID3D11RenderTargetView* expectedRtv,
    ID3D11BlendState* expectedBlendState) noexcept {
    if (!expectedBlendState ||
        !verified_linear_full_target_draw_ready(
            vb, context, startVertex, vertexCount, generation, vbVersion,
            targetWidth, targetHeight, targetFormat, expectedRtv))
        return false;

    Microsoft::WRL::ComPtr<ID3D11BlendState> liveBlend;
    FLOAT factors[4] = {};
    UINT mask = 0;
    context->OMGetBlendState(liveBlend.GetAddressOf(), factors, &mask);
    if (liveBlend.Get() != expectedBlendState ||
        mask != D3D11_DEFAULT_SAMPLE_MASK)
        return false;
    for (const auto factor : factors)
        if (factor != 1.0f) return false;

    Microsoft::WRL::ComPtr<ID3D11Device> device, blendDevice;
    context->GetDevice(device.GetAddressOf());
    expectedBlendState->GetDevice(blendDevice.GetAddressOf());
    if (!device || blendDevice.Get() != device.Get())
        return false;
    D3D11_BLEND_DESC desc{};
    expectedBlendState->GetDesc(&desc);
    const auto& rt = desc.RenderTarget[0];
    // Only source-alpha RGB with unchanged source alpha and full write mask
    // is proven; other D3D9 factors and multiple targets require separate gates.
    if (desc.AlphaToCoverageEnable || desc.IndependentBlendEnable ||
        !rt.BlendEnable ||
        rt.SrcBlend != D3D11_BLEND_SRC_ALPHA ||
        rt.DestBlend != D3D11_BLEND_INV_SRC_ALPHA ||
        rt.BlendOp != D3D11_BLEND_OP_ADD ||
        rt.SrcBlendAlpha != D3D11_BLEND_ONE ||
        rt.DestBlendAlpha != D3D11_BLEND_ZERO ||
        rt.BlendOpAlpha != D3D11_BLEND_OP_ADD ||
        rt.RenderTargetWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL)
        return false;
    return true;
}
} // namespace outrun::vr::dx11
