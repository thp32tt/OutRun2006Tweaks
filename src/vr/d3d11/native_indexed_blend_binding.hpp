#pragma once
// R190: dormant native indexed Draw blend-state ownership and OM output semantics.
// Never dispatches game Draw; the isolated WARP probe performs actual GPU DrawIndexed.
#include "native_indexed_target_viewport.hpp"
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_indexed_blend_draw_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    ID3D11DeviceContext* context, UINT startIndex, UINT indexCount, INT baseVertex,
    std::uint64_t generation, std::uint64_t vbVersion, std::uint64_t ibVersion,
    UINT targetWidth, UINT targetHeight, DXGI_FORMAT targetFormat,
    ID3D11RenderTargetView* expectedRtv,
    ID3D11BlendState* expectedBlendState) noexcept {
    if (!expectedBlendState ||
        !verified_indexed_full_target_draw_ready(
            vb, ib, context, startIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion, targetWidth, targetHeight,
            targetFormat, expectedRtv))
        return false;

    Microsoft::WRL::ComPtr<ID3D11BlendState> liveBlendState;
    FLOAT blendFactors[4] = {};
    UINT sampleMask = 0;
    context->OMGetBlendState(liveBlendState.GetAddressOf(), blendFactors, &sampleMask);
    if (liveBlendState.Get() != expectedBlendState ||
        sampleMask != D3D11_DEFAULT_SAMPLE_MASK)
        return false;
    for (const auto factor : blendFactors) {
        if (factor != 1.0f) return false;
    }
    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice, blendDevice;
    context->GetDevice(contextDevice.GetAddressOf());
    expectedBlendState->GetDevice(blendDevice.GetAddressOf());
    if (!contextDevice || contextDevice.Get() != blendDevice.Get())
        return false;

    D3D11_BLEND_DESC desc{};
    expectedBlendState->GetDesc(&desc);
    const auto& target = desc.RenderTarget[0];
    // R190 models one explicitly owned RGBA output and conventional source alpha.
    // More complex D3D9 blend factors must be translated and verified separately.
    if (desc.AlphaToCoverageEnable || desc.IndependentBlendEnable ||
        !target.BlendEnable ||
        target.SrcBlend != D3D11_BLEND_SRC_ALPHA ||
        target.DestBlend != D3D11_BLEND_INV_SRC_ALPHA ||
        target.BlendOp != D3D11_BLEND_OP_ADD ||
        target.SrcBlendAlpha != D3D11_BLEND_ONE ||
        target.DestBlendAlpha != D3D11_BLEND_ZERO ||
        target.BlendOpAlpha != D3D11_BLEND_OP_ADD ||
        target.RenderTargetWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL)
        return false;
    return true;
}
} // namespace outrun::vr::dx11
