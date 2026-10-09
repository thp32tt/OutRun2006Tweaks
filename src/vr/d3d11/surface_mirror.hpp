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

        // R165 diagnostic-only: copy the current non-MSAA color mirror to a
        // CPU-readable staging texture on its own immediate D3D11 context.
        // Never exposes a game Draw path or changes the active OM binding.
        [[nodiscard]] bool copy_color_to_staging(
            ID3D11DeviceContext* context,
            ID3D11Texture2D** stagingOutput) const noexcept;

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
        [[nodiscard]] std::uint64_t mirror_serial() const noexcept {
            return mirror_serial_;
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
        // Monotonic per-owner recreation identity. Deliberately survives
        // shutdown()/reinitialize so stale pair snapshots cannot become current.
        std::uint64_t mirror_serial_ = 0;

        Microsoft::WRL::ComPtr<ID3D11Device> device_;
        Microsoft::WRL::ComPtr<ID3D11Texture2D> texture_;
        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv_;
        Microsoft::WRL::ComPtr<ID3D11DepthStencilView> dsv_;
    };

    // R119 composes one exact color/depth mirror pair into a fail-closed
    // render-target readiness identity. Dormant evidence only: no OM binding
    // or game Draw* routing is activated here.
    struct NativeSurfacePairReadiness
    {
        bool inputValid{};
        bool colorReady{};
        bool depthReady{};
        bool deviceMatches{};
        bool dimensionsMatch{};
        bool generationsCurrent{};
        bool componentSerialsPresent{};
        bool ready{};
        UINT width{};
        UINT height{};
        std::uint64_t colorMirrorSerial{};
        std::uint64_t depthMirrorSerial{};
        std::uint64_t snapshotToken{};
    };

    [[nodiscard]] NativeSurfacePairReadiness compose_surface_pair_readiness(
        ID3D11Device* expectedDevice,
        const NativeSurfaceMirror& color,
        const NativeSurfaceMirror& depth) noexcept;

    [[nodiscard]] bool validate_surface_pair_snapshot(
        ID3D11Device* expectedDevice,
        const NativeSurfaceMirror& color,
        const NativeSurfaceMirror& depth,
        std::uint64_t snapshotToken) noexcept;

    // R145 observes the effective OM render-target/depth-target state after
    // the dormant R130 owner has been applied. A token is issued only while
    // the sealed surface-pair mirrors are still current and the exact RTV/DSV
    // are live on the caller-supplied same-device context.
    struct NativeSurfacePairBindingReadiness
    {
        bool inputValid{};
        bool ownerReady{};
        bool pairCurrent{};
        bool contextMatches{};
        bool colorViewCurrent{};
        bool depthViewCurrent{};
        bool rtvBoundExact{};
        bool dsvBoundExact{};
        bool unorderedAccessClear{};
        bool ready{};
        std::uint64_t surfacePairSnapshotToken{};
        std::uint64_t snapshotToken{};
    };

    // R130 consumes one sealed R119 surface-pair identity into a dormant
    // OM render-target binding owner. apply() revalidates the live mirrors
    // before binding, so Reset/recreation invalidates stale owners. No game
    // Draw* path constructs or calls this owner.
    class NativeSurfacePairBinding final
    {
    public:
        NativeSurfacePairBinding() = default;
        ~NativeSurfacePairBinding() = default;
        NativeSurfacePairBinding(const NativeSurfacePairBinding&) = delete;
        NativeSurfacePairBinding& operator=(const NativeSurfacePairBinding&) = delete;

        bool initialize(
            ID3D11Device* device,
            const NativeSurfaceMirror& color,
            const NativeSurfaceMirror& depth,
            const NativeSurfacePairReadiness& readiness) noexcept;
        void shutdown() noexcept;
        [[nodiscard]] bool apply(
            ID3D11DeviceContext* context,
            const NativeSurfaceMirror& color,
            const NativeSurfaceMirror& depth) const noexcept;
        [[nodiscard]] NativeSurfacePairBindingReadiness binding_readiness(
            ID3D11DeviceContext* context,
            const NativeSurfaceMirror& color,
            const NativeSurfaceMirror& depth) const noexcept;
        [[nodiscard]] bool validate_binding_snapshot(
            ID3D11DeviceContext* context,
            const NativeSurfaceMirror& color,
            const NativeSurfaceMirror& depth,
            std::uint64_t snapshotToken) const noexcept;

        [[nodiscard]] bool ready() const noexcept
        {
            return device_ && rtv_ && dsv_ && surface_pair_snapshot_token_ != 0;
        }
        [[nodiscard]] std::uint64_t surface_pair_snapshot_token() const noexcept
        {
            return surface_pair_snapshot_token_;
        }

    private:
        Microsoft::WRL::ComPtr<ID3D11Device> device_;
        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv_;
        Microsoft::WRL::ComPtr<ID3D11DepthStencilView> dsv_;
        std::uint64_t surface_pair_snapshot_token_ = 0;
    };
}
