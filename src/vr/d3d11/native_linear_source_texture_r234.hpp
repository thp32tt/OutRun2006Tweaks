#pragma once
// R234: a live D3D9 A8B8G8R8 CPU snapshot owns exactly one immutable
// D3D11 Texture2D/SRV revision. No gameplay hook or Draw activation.
#include "native_linear_texture_binding.hpp"
#include <cstddef>
#include <cstdint>
#include <utility>
#include <wrl/client.h>

namespace outrun::vr::dx11 {
class NativeLinearSourceTextureR234 final {
public:
    bool initialize(ID3D11Device* device, D3DFORMAT sourceFormat,
                    const void* sourceBytes, std::size_t availableBytes,
                    UINT width, UINT height, UINT rowPitch,
                    std::uint64_t generation, std::uint64_t sourceVersion) noexcept {
        shutdown();
        if (!device || !sourceBytes || !width || !height || !generation ||
            !sourceVersion || sourceFormat != D3DFMT_A8B8G8R8 ||
            width > UINT32_MAX / 4u || rowPitch < width * 4u)
            return false;
        const std::uint64_t required =
            std::uint64_t(rowPitch) * (height - 1u) + std::uint64_t(width) * 4u;
        if (required > static_cast<std::uint64_t>(availableBytes))
            return false;
        D3D11_TEXTURE2D_DESC desc{};
        desc.Width = width;
        desc.Height = height;
        desc.MipLevels = 1u;
        desc.ArraySize = 1u;
        desc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
        desc.SampleDesc.Count = 1u;
        desc.Usage = D3D11_USAGE_IMMUTABLE;
        desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
        D3D11_SUBRESOURCE_DATA data{};
        data.pSysMem = sourceBytes;
        data.SysMemPitch = rowPitch;
        Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
        if (FAILED(device->CreateTexture2D(&desc, &data, texture.GetAddressOf())) ||
            !texture)
            return false;
        Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> view;
        if (FAILED(device->CreateShaderResourceView(
                texture.Get(), nullptr, view.GetAddressOf())) || !view)
            return false;
        device_ = device;
        texture_ = std::move(texture);
        view_ = std::move(view);
        generation_ = generation;
        sourceVersion_ = sourceVersion;
        return descriptor_exact();
    }

    bool bind_ps(ID3D11DeviceContext* context, UINT slot,
                 std::uint64_t generation,
                 std::uint64_t sourceVersion) const noexcept {
        if (slot >= D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT ||
            !same_immediate_device(context) || !descriptor_exact() ||
            generation != generation_ || sourceVersion != sourceVersion_)
            return false;
        ID3D11ShaderResourceView* view = view_.Get();
        context->PSSetShaderResources(slot, 1u, &view);
        return binding_exact(context, slot, generation, sourceVersion);
    }

    bool binding_exact(ID3D11DeviceContext* context, UINT slot,
                       std::uint64_t generation,
                       std::uint64_t sourceVersion) const noexcept {
        if (slot >= D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT ||
            !same_immediate_device(context) || !descriptor_exact() ||
            generation != generation_ || sourceVersion != sourceVersion_)
            return false;
        Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> live;
        context->PSGetShaderResources(slot, 1u, live.GetAddressOf());
        return live.Get() == view_.Get();
    }

    [[nodiscard]] ID3D11ShaderResourceView* view() const noexcept {
        return view_.Get();
    }
    [[nodiscard]] ID3D11Texture2D* texture() const noexcept {
        return texture_.Get();
    }
    void shutdown() noexcept {
        view_.Reset();
        texture_.Reset();
        device_.Reset();
        generation_ = 0;
        sourceVersion_ = 0;
    }

private:
    bool same_immediate_device(ID3D11DeviceContext* context) const noexcept {
        if (!context || !device_ ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> live;
        context->GetDevice(live.GetAddressOf());
        return live.Get() == device_.Get();
    }

    bool descriptor_exact() const noexcept {
        if (!device_ || !texture_ || !view_ || !generation_ || !sourceVersion_)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> owner;
        texture_->GetDevice(owner.GetAddressOf());
        if (owner.Get() != device_.Get()) return false;
        owner.Reset();
        view_->GetDevice(owner.GetAddressOf());
        if (owner.Get() != device_.Get()) return false;
        D3D11_TEXTURE2D_DESC desc{};
        texture_->GetDesc(&desc);
        if (!desc.Width || !desc.Height || desc.MipLevels != 1u ||
            desc.ArraySize != 1u || desc.Format != DXGI_FORMAT_R8G8B8A8_UNORM ||
            desc.SampleDesc.Count != 1u || desc.SampleDesc.Quality != 0u ||
            desc.Usage != D3D11_USAGE_IMMUTABLE ||
            desc.BindFlags != D3D11_BIND_SHADER_RESOURCE ||
            desc.CPUAccessFlags != 0u || desc.MiscFlags != 0u)
            return false;
        D3D11_SHADER_RESOURCE_VIEW_DESC srv{};
        view_->GetDesc(&srv);
        return srv.Format == desc.Format &&
            srv.ViewDimension == D3D11_SRV_DIMENSION_TEXTURE2D &&
            srv.Texture2D.MostDetailedMip == 0u && srv.Texture2D.MipLevels == 1u;
    }

    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> texture_;
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> view_;
    std::uint64_t generation_ = 0;
    std::uint64_t sourceVersion_ = 0;
};

// Connected producer-to-consumer readiness: source data/version -> owned
// immutable native texture/SRV -> bound pixel stage -> exact mono output.
// No production Draw; the isolated WARP probe owns GPU dispatch.
[[nodiscard]] inline bool verified_linear_source_texture_draw_ready(
    const NativeLinearSourceTextureR234& owner,
    const NativeLinearBufferMirror& vb,
    ID3D11DeviceContext* context,
    UINT firstVertex, UINT vertexCount,
    std::uint64_t generation, std::uint64_t vbVersion,
    std::uint64_t sourceVersion, UINT width, UINT height,
    DXGI_FORMAT targetFormat, ID3D11RenderTargetView* expectedRtv,
    ID3D11SamplerState* sampler) noexcept {
    return owner.binding_exact(context, 0u, generation, sourceVersion) &&
           verified_linear_textured_draw_ready(
               vb, context, firstVertex, vertexCount,
               generation, vbVersion, width, height, targetFormat,
               expectedRtv, 0u, owner.view(), sampler,
               DXGI_FORMAT_R8G8B8A8_UNORM);
}
} // namespace outrun::vr::dx11
