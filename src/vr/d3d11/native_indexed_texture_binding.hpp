#pragma once
// R188: dormant native indexed draw PS texture/sampler identity and hazard fence.
// The caller owns expected SRV/sampler lifetime. This helper never dispatches Draw*.
#include "native_indexed_target_viewport.hpp"
#include <wrl/client.h>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool verified_indexed_textured_draw_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    ID3D11DeviceContext* context, UINT startIndex, UINT indexCount, INT baseVertex,
    std::uint64_t generation, std::uint64_t vbVersion, std::uint64_t ibVersion,
    UINT targetWidth, UINT targetHeight, DXGI_FORMAT targetFormat,
    ID3D11RenderTargetView* expectedTarget, UINT psSlot, ID3D11ShaderResourceView* expectedSrv,
    ID3D11SamplerState* expectedSampler, DXGI_FORMAT textureFormat) noexcept {
    if (!expectedSrv || !expectedSampler ||
        psSlot >= D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT ||
        psSlot >= D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT ||
        textureFormat == DXGI_FORMAT_UNKNOWN ||
        !verified_indexed_full_target_draw_ready(
            vb, ib, context, startIndex, indexCount, baseVertex,
            generation, vbVersion, ibVersion, targetWidth, targetHeight, targetFormat,
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
        // R228: an untracked DEFAULT/dynamic texture or a writable RTV/UAV
        // alias has no immutable D3D9 source-revision receipt. Keep native
        // indexed texture readiness opt-in until an update/lifetime owner exists.
        desc.Usage != D3D11_USAGE_IMMUTABLE ||
        desc.CPUAccessFlags != 0 || desc.MiscFlags != 0 ||
        desc.BindFlags != D3D11_BIND_SHADER_RESOURCE)
        return false;

    // R223: R187 seals the indexed color RTV and optional DSV, but R188
    // has no pixel UAV owner. A hidden OM UAV can write a second-eye resource
    // during a textured DrawIndexed even when the only RTV is owned.
    ID3D11RenderTargetView* liveRtv[1]{};
    ID3D11DepthStencilView* liveDsv = nullptr;
    ID3D11UnorderedAccessView* liveUavs[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    context->OMGetRenderTargetsAndUnorderedAccessViews(
        1u, liveRtv, &liveDsv, 0u, D3D11_PS_CS_UAV_REGISTER_COUNT, liveUavs);
    bool isolated = liveRtv[0] == expectedTarget && !liveDsv;
    if (liveRtv[0]) liveRtv[0]->Release();
    if (liveDsv) liveDsv->Release();
    // Each OMGet result owns one reference, including rejection paths.
    for (auto* uav : liveUavs) {
        if (uav) {
            isolated = false;
            uav->Release();
        }
    }
    if (!isolated) return false;
    // A shader read of the active render target is undefined. D3D11 can
    // silently unbind an aliased SRV; require separate source/eye resources.
    Microsoft::WRL::ComPtr<ID3D11Resource> output;
    expectedTarget->GetResource(output.GetAddressOf());
    return output && output.Get() != source.Get();
}
} // namespace outrun::vr::dx11
