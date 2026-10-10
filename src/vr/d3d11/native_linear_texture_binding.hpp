#pragma once
// R203: dormant native non-indexed Draw PS SRV/sampler identity and read/write hazard fence.
// The caller owns expected SRV/sampler lifetime. This helper never dispatches Draw.
#include "native_linear_target_viewport.hpp"
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_linear_textured_draw_ready(
    const NativeLinearBufferMirror& vb, ID3D11DeviceContext* context,
    UINT startVertex, UINT vertexCount,
    std::uint64_t generation, std::uint64_t vbVersion,
    UINT targetWidth, UINT targetHeight, DXGI_FORMAT targetFormat,
    ID3D11RenderTargetView* expectedTarget, UINT psSlot, ID3D11ShaderResourceView* expectedSrv,
    ID3D11SamplerState* expectedSampler, DXGI_FORMAT textureFormat) noexcept {
    if (!expectedSrv || !expectedSampler ||
        psSlot >= D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT ||
        psSlot >= D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT ||
        textureFormat == DXGI_FORMAT_UNKNOWN ||
        !verified_linear_full_target_draw_ready(
            vb, context, startVertex, vertexCount,
            generation, vbVersion, targetWidth, targetHeight, targetFormat,
            expectedTarget))
        return false;

    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> liveSrv;
    Microsoft::WRL::ComPtr<ID3D11SamplerState> liveSampler;
    context->PSGetShaderResources(psSlot, 1, liveSrv.GetAddressOf());
    context->PSGetSamplers(psSlot, 1, liveSampler.GetAddressOf());
    if (liveSrv.Get() != expectedSrv || liveSampler.Get() != expectedSampler)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> device, srvDevice, samplerDevice;
    context->GetDevice(device.GetAddressOf());
    expectedSrv->GetDevice(srvDevice.GetAddressOf());
    expectedSampler->GetDevice(samplerDevice.GetAddressOf());
    if (!device || srvDevice.Get() != device.Get() ||
        samplerDevice.Get() != device.Get())
        return false;

    D3D11_SHADER_RESOURCE_VIEW_DESC view{};
    expectedSrv->GetDesc(&view);
    if (view.ViewDimension != D3D11_SRV_DIMENSION_TEXTURE2D ||
        view.Texture2D.MostDetailedMip != 0 || view.Texture2D.MipLevels != 1 ||
        view.Format != textureFormat)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Resource> source;
    expectedSrv->GetResource(source.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
    if (!source || FAILED(source.As(&texture)) || !texture)
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    texture->GetDesc(&desc);
    if (!desc.Width || !desc.Height || desc.MipLevels != 1 ||
        desc.ArraySize != 1 || desc.SampleDesc.Count != 1 ||
        desc.SampleDesc.Quality != 0 || desc.Format != textureFormat ||
        !(desc.BindFlags & D3D11_BIND_SHADER_RESOURCE))
        return false;

    // An eye's native non-indexed Draw owns exactly one OM output.
    // Even an unrelated stale RTV in slot 1+ would receive this Draw:
    // reject all extra eye/MRT bindings, not just a slot-0 SRV alias.
    ID3D11RenderTargetView* liveOutputs[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT] = {};
    Microsoft::WRL::ComPtr<ID3D11DepthStencilView> liveDepth;
    context->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
                                liveOutputs, liveDepth.GetAddressOf());
    // R222: R203 has no depth-owner parameter. A retained DSV can suppress
    // fragments or couple eyes even with an exact RTV/SRV pair. Fail closed
    // rather than treating an unowned depth surface as proven readiness.
    bool singleEyeTarget = liveOutputs[0] == expectedTarget && !liveDepth;
    for (UINT index = 1; index < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++index)
        if (liveOutputs[index]) singleEyeTarget = false;
    for (auto* boundView : liveOutputs)
        if (boundView) boundView->Release(); // OMGetRenderTargets added a COM reference.
    if (!singleEyeTarget) return false;
    // A shader read of the active output is undefined even for one RTV.
    Microsoft::WRL::ComPtr<ID3D11Resource> output;
    expectedTarget->GetResource(output.GetAddressOf());
    return output && output.Get() != source.Get();
}
} // namespace outrun::vr::dx11
