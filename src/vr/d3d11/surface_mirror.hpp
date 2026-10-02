#pragma once

#include <cstdint>
#include <d3d9.h>
#include <d3d11.h>
#include <wrl/client.h>

#include "resource_translation.hpp"

namespace outrun::vr::dx11
{
    // Dormant R118 owner for DEFAULT-pool D3D9 render-target/depth-stencil
    // surfaces. The mirror is generation-bound: a successful D3D9 Reset
    // invalidates the D3D11 Texture2D/view and requires explicit recreation.
    // This class does not bind a native draw path.
    class NativeSurfaceMirror final
    {
    public:
        NativeSurfaceMirror() = default;
        ~NativeSurfaceMirror() = default;
        NativeSurfaceMirror(const NativeSurfaceMirror&) = delete;
        NativeSurfaceMirror& operator=(const NativeSurfaceMirror&) = delete;

        bool initialize(
            ID3D11Device* device,
            ResourceRole role,
            UINT width,
            UINT height,
            D3DFORMAT sourceFormat,
            D3DPOOL sourcePool,
            DWORD sourceUsage,
            D3DMULTISAMPLE_TYPE sourceMultisampleType,
            DWORD sourceMultisampleQuality) noexcept;

        bool recreate(ID3D11Device* device) noexcept;
        void observe_device_reset() noexcept;
        void shutdown() noexcept;

        [[nodiscard]] bool ready() const noexcept;
        [[nodiscard]] bool descriptor_exact(
            ID3D11Device* expectedDevice) const noexcept;

        [[nodiscard]] ResourceRole role() const noexcept { return role_; }
        [[nodiscard]] UINT width() const noexcept { return width_; }
        [[nodiscard]] UINT height() const noexcept { return height_; }
        [[nodiscard]] D3DFORMAT source_format() const noexcept {
            return source_format_;
        }
        [[nodiscard]] std::uint64_t device_generation() const noexcept {
            return device_generation_;
        }
        [[nodiscard]] std::uint64_t mirror_generation() const noexcept {
            return mirror_generation_;
        }
        [[nodiscard]] ID3D11Texture2D* texture() const noexcept {
            return texture_.Get();
        }
        [[nodiscard]] ID3D11RenderTargetView* render_target_view() const noexcept {
            return rtv_.Get();
        }
        [[nodiscard]] ID3D11DepthStencilView* depth_stencil_view() const noexcept {
            return dsv_.Get();
        }

    private:
        [[nodiscard]] bool source_descriptor_exact() const noexcept;
        void release_mirror() noexcept;

        ResourceRole role_ = ResourceRole::Color;
        UINT width_ = 0;
        UINT height_ = 0;
        D3DFORMAT source_format_ = D3DFMT_UNKNOWN;
        D3DPOOL source_pool_ = D3DPOOL_DEFAULT;
        DWORD source_usage_ = 0;
        D3DMULTISAMPLE_TYPE source_multisample_type_ = D3DMULTISAMPLE_NONE;
        DWORD source_multisample_quality_ = 0;
        bool metadata_valid_ = false;
        std::uint64_t device_generation_ = 1;
        std::uint64_t mirror_generation_ = 0;

        Microsoft::WRL::ComPtr<ID3D11Device> device_;
        Microsoft::WRL::ComPtr<ID3D11Texture2D> texture_;
        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv_;
        Microsoft::WRL::ComPtr<ID3D11DepthStencilView> dsv_;
    };
}
