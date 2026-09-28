#include "native_shared_eye_ring.hpp"

#include <dxgi.h>

namespace outrun::vr::dx11
{
    namespace
    {
        bool create_shared_eye(
            ID3D11Device* device,
            const D3D11_TEXTURE2D_DESC& desc,
            Microsoft::WRL::ComPtr<ID3D11Texture2D>& texture,
            Microsoft::WRL::ComPtr<ID3D11RenderTargetView>& rtv,
            HANDLE& handle) noexcept
        {
            handle = nullptr;
            if (FAILED(device->CreateTexture2D(
                    &desc, nullptr, texture.ReleaseAndGetAddressOf())) ||
                !texture)
                return false;

            if (FAILED(device->CreateRenderTargetView(
                    texture.Get(), nullptr, rtv.ReleaseAndGetAddressOf())) ||
                !rtv)
                return false;

            Microsoft::WRL::ComPtr<IDXGIResource> dxgiResource;
            if (FAILED(texture->QueryInterface(
                    __uuidof(IDXGIResource),
                    reinterpret_cast<void**>(
                        dxgiResource.ReleaseAndGetAddressOf()))) ||
                !dxgiResource)
                return false;

            // Legacy shared handles are deliberate here. The current x64 host
            // consumes producer handles through ID3D11Device::OpenSharedResource,
            // so using NT handles would require a new protocol/open path.
            if (FAILED(dxgiResource->GetSharedHandle(&handle)) || !handle)
                return false;

            return true;
        }
    }

    bool NativeSharedEyeRing::initialize(
        ID3D11Device* device,
        std::uint32_t width,
        std::uint32_t height,
        DXGI_FORMAT format) noexcept
    {
        shutdown();
        if (!device || width == 0 || height == 0 ||
            format == DXGI_FORMAT_UNKNOWN)
            return false;

        D3D11_TEXTURE2D_DESC desc{};
        desc.Width = width;
        desc.Height = height;
        desc.MipLevels = 1;
        desc.ArraySize = 1;
        desc.Format = format;
        desc.SampleDesc.Count = 1;
        desc.Usage = D3D11_USAGE_DEFAULT;
        desc.BindFlags =
            D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;
        desc.MiscFlags = D3D11_RESOURCE_MISC_SHARED;

        D3D11_QUERY_DESC query{};
        query.Query = D3D11_QUERY_EVENT;

        for (auto& slot : slots_)
        {
            for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
            {
                if (!create_shared_eye(
                        device, desc,
                        slot.eye[eyeIndex],
                        slot.rtv[eyeIndex],
                        slot.shared_handle[eyeIndex]))
                {
                    shutdown();
                    return false;
                }
            }

            if (FAILED(device->CreateQuery(
                    &query, slot.producer_fence.ReleaseAndGetAddressOf())) ||
                !slot.producer_fence)
            {
                shutdown();
                return false;
            }
        }

        width_ = width;
        height_ = height;
        format_ = format;
        ready_ = true;
        return true;
    }

    void NativeSharedEyeRing::shutdown() noexcept
    {
        for (auto& slot : slots_)
        {
            slot.producer_fence.Reset();
            for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
            {
                slot.rtv[eyeIndex].Reset();
                slot.eye[eyeIndex].Reset();
                // GetSharedHandle returns a legacy shared-resource handle whose
                // lifetime follows the resource; do not CloseHandle it.
                slot.shared_handle[eyeIndex] = nullptr;
            }
        }
        width_ = 0;
        height_ = 0;
        format_ = DXGI_FORMAT_UNKNOWN;
        ready_ = false;
    }

    ID3D11Texture2D* NativeSharedEyeRing::eye(
        std::uint32_t slot, std::uint32_t eye_index) const noexcept
    {
        if (slot >= slots_.size() || eye_index >= 2)
            return nullptr;
        return slots_[slot].eye[eye_index].Get();
    }

    ID3D11RenderTargetView* NativeSharedEyeRing::rtv(
        std::uint32_t slot, std::uint32_t eye_index) const noexcept
    {
        if (slot >= slots_.size() || eye_index >= 2)
            return nullptr;
        return slots_[slot].rtv[eye_index].Get();
    }

    HANDLE NativeSharedEyeRing::shared_handle(
        std::uint32_t slot, std::uint32_t eye_index) const noexcept
    {
        if (slot >= slots_.size() || eye_index >= 2)
            return nullptr;
        return slots_[slot].shared_handle[eye_index];
    }

    ID3D11Query* NativeSharedEyeRing::producer_fence(
        std::uint32_t slot) const noexcept
    {
        if (slot >= slots_.size())
            return nullptr;
        return slots_[slot].producer_fence.Get();
    }
}
