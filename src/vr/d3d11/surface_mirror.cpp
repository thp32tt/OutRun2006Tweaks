#include "surface_mirror.hpp"

#include <utility>

namespace outrun::vr::dx11
{
    bool NativeSurfaceMirror::initialize(
        ID3D11Device* device,
        ResourceRole role,
        UINT width,
        UINT height,
        D3DFORMAT sourceFormat,
        D3DPOOL sourcePool,
        DWORD sourceUsage,
        D3DMULTISAMPLE_TYPE sourceMultisampleType,
        DWORD sourceMultisampleQuality) noexcept
    {
        shutdown();

        role_ = role;
        width_ = width;
        height_ = height;
        source_format_ = sourceFormat;
        source_pool_ = sourcePool;
        source_usage_ = sourceUsage;
        source_multisample_type_ = sourceMultisampleType;
        source_multisample_quality_ = sourceMultisampleQuality;
        metadata_valid_ = source_descriptor_exact();
        if (!metadata_valid_)
            return false;

        return recreate(device);
    }

    bool NativeSurfaceMirror::source_descriptor_exact() const noexcept
    {
        if ((role_ != ResourceRole::Color &&
             role_ != ResourceRole::DepthStencil) ||
            width_ == 0 || height_ == 0)
            return false;

        // D3D9 and DXGI multisample quality semantics are not assumed to be
        // interchangeable. Keep non-MSAA surfaces exact and fail closed until
        // an adapter/quality-level translation is proven.
        if (source_multisample_type_ != D3DMULTISAMPLE_NONE ||
            source_multisample_quality_ != 0)
            return false;

        const auto format = translate_resource_format(source_format_, role_);
        const auto behavior =
            translate_resource_behavior(role_, source_pool_, source_usage_);
        const UINT expectedBind =
            role_ == ResourceRole::Color
                ? D3D11_BIND_RENDER_TARGET
                : D3D11_BIND_DEPTH_STENCIL;
        return format.exact &&
            behavior.descriptorExact &&
            behavior.lifetime == ResourceMirrorLifetime::DeviceGeneration &&
            behavior.usage == D3D11_USAGE_DEFAULT &&
            behavior.bindFlags == expectedBind &&
            behavior.cpuAccessFlags == 0 &&
            !behavior.requiresCpuShadow &&
            !behavior.requiresMutationTelemetry;
    }

    bool NativeSurfaceMirror::recreate(ID3D11Device* device) noexcept
    {
        release_mirror();
        if (!metadata_valid_ || !device || !source_descriptor_exact())
            return false;

        const auto format = translate_resource_format(source_format_, role_);
        const auto behavior =
            translate_resource_behavior(role_, source_pool_, source_usage_);
        if (!format.exact || !behavior.descriptorExact)
            return false;

        D3D11_TEXTURE2D_DESC textureDesc{};
        textureDesc.Width = width_;
        textureDesc.Height = height_;
        textureDesc.MipLevels = 1;
        textureDesc.ArraySize = 1;
        textureDesc.Format = format.format;
        textureDesc.SampleDesc.Count = 1;
        textureDesc.SampleDesc.Quality = 0;
        textureDesc.Usage = behavior.usage;
        textureDesc.BindFlags = behavior.bindFlags;
        textureDesc.CPUAccessFlags = behavior.cpuAccessFlags;
        textureDesc.MiscFlags = 0;

        Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
        if (FAILED(device->CreateTexture2D(
                &textureDesc, nullptr, texture.ReleaseAndGetAddressOf())) ||
            !texture)
            return false;

        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv;
        Microsoft::WRL::ComPtr<ID3D11DepthStencilView> dsv;
        if (role_ == ResourceRole::Color)
        {
            D3D11_RENDER_TARGET_VIEW_DESC viewDesc{};
            viewDesc.Format = format.format;
            viewDesc.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2D;
            viewDesc.Texture2D.MipSlice = 0;
            if (FAILED(device->CreateRenderTargetView(
                    texture.Get(), &viewDesc, rtv.ReleaseAndGetAddressOf())) ||
                !rtv)
                return false;
        }
        else
        {
            D3D11_DEPTH_STENCIL_VIEW_DESC viewDesc{};
            viewDesc.Format = format.format;
            viewDesc.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
            viewDesc.Flags = 0;
            viewDesc.Texture2D.MipSlice = 0;
            if (FAILED(device->CreateDepthStencilView(
                    texture.Get(), &viewDesc, dsv.ReleaseAndGetAddressOf())) ||
                !dsv)
                return false;
        }

        device_ = device;
        texture_ = std::move(texture);
        rtv_ = std::move(rtv);
        dsv_ = std::move(dsv);
        mirror_generation_ = device_generation_;
        return descriptor_exact(device);
    }

    bool NativeSurfaceMirror::ready() const noexcept
    {
        if (!metadata_valid_ || !device_ || !texture_ ||
            mirror_generation_ == 0 ||
            mirror_generation_ != device_generation_)
            return false;

        return role_ == ResourceRole::Color
            ? rtv_.Get() != nullptr && dsv_.Get() == nullptr
            : role_ == ResourceRole::DepthStencil &&
                dsv_.Get() != nullptr && rtv_.Get() == nullptr;
    }

    bool NativeSurfaceMirror::descriptor_exact(
        ID3D11Device* expectedDevice) const noexcept
    {
        if (!ready() || !expectedDevice || device_.Get() != expectedDevice)
            return false;

        const auto format = translate_resource_format(source_format_, role_);
        const auto behavior =
            translate_resource_behavior(role_, source_pool_, source_usage_);
        if (!format.exact || !behavior.descriptorExact)
            return false;

        D3D11_TEXTURE2D_DESC textureDesc{};
        texture_->GetDesc(&textureDesc);
        if (textureDesc.Width != width_ ||
            textureDesc.Height != height_ ||
            textureDesc.MipLevels != 1 ||
            textureDesc.ArraySize != 1 ||
            textureDesc.Format != format.format ||
            textureDesc.SampleDesc.Count != 1 ||
            textureDesc.SampleDesc.Quality != 0 ||
            textureDesc.Usage != D3D11_USAGE_DEFAULT ||
            textureDesc.BindFlags != behavior.bindFlags ||
            textureDesc.CPUAccessFlags != 0 ||
            textureDesc.MiscFlags != 0)
            return false;

        Microsoft::WRL::ComPtr<ID3D11Device> textureDevice;
        texture_->GetDevice(textureDevice.ReleaseAndGetAddressOf());
        if (!textureDevice || textureDevice.Get() != expectedDevice)
            return false;

        if (role_ == ResourceRole::Color)
        {
            D3D11_RENDER_TARGET_VIEW_DESC viewDesc{};
            rtv_->GetDesc(&viewDesc);
            return viewDesc.Format == format.format &&
                viewDesc.ViewDimension == D3D11_RTV_DIMENSION_TEXTURE2D &&
                viewDesc.Texture2D.MipSlice == 0;
        }

        D3D11_DEPTH_STENCIL_VIEW_DESC viewDesc{};
        dsv_->GetDesc(&viewDesc);
        return viewDesc.Format == format.format &&
            viewDesc.ViewDimension == D3D11_DSV_DIMENSION_TEXTURE2D &&
            viewDesc.Flags == 0 &&
            viewDesc.Texture2D.MipSlice == 0;
    }

    void NativeSurfaceMirror::observe_device_reset() noexcept
    {
        release_mirror();
        device_generation_ =
            device_generation_ == ~std::uint64_t{0}
                ? 1
                : device_generation_ + 1;
    }

    void NativeSurfaceMirror::release_mirror() noexcept
    {
        dsv_.Reset();
        rtv_.Reset();
        texture_.Reset();
        device_.Reset();
        mirror_generation_ = 0;
    }

    void NativeSurfaceMirror::shutdown() noexcept
    {
        release_mirror();
        role_ = ResourceRole::Color;
        width_ = 0;
        height_ = 0;
        source_format_ = D3DFMT_UNKNOWN;
        source_pool_ = D3DPOOL_DEFAULT;
        source_usage_ = 0;
        source_multisample_type_ = D3DMULTISAMPLE_NONE;
        source_multisample_quality_ = 0;
        metadata_valid_ = false;
        device_generation_ = 1;
    }
}
