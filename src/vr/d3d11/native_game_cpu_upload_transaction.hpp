#pragma once
#include <Windows.h>
#include <d3d9.h>
#include <wrl/client.h>
#include <cstdint>
#include "native_game_cpu_upload_plan.hpp"

namespace outrun::vr::dx11::live_game_frame {
// GPU-owned backup for the native full-frame *CPU staging* publication path.
// D3D9 UpdateSurface is not an atomic commit if the driver returns failure.
// The separate D3D11 shared-desktop presenter owns its own rollback.
class NativeGameCpuUploadTransaction final {
public:
    NativeGameCpuUploadTransaction() = default;
    NativeGameCpuUploadTransaction(const NativeGameCpuUploadTransaction&) = delete;
    NativeGameCpuUploadTransaction& operator=(const NativeGameCpuUploadTransaction&) = delete;
    void reset() noexcept {
        backup_.Reset(); owner_.Reset(); active_ = {};
        width_ = height_ = tileWidth_ = tileHeight_ = 0u;
        generation_ = 0u; format_ = D3DFMT_UNKNOWN;
        armed_ = false; faulted_ = false;
    }
    [[nodiscard]] bool capture(IDirect3DDevice9* game,
        IDirect3DSurface9* backbuffer, std::uint32_t width,
        std::uint32_t height, D3DFORMAT format,
        std::uint64_t generation, NativeGameCpuUploadPlan plan) noexcept {
        armed_ = false;
        if (faulted_ || !game || !backbuffer || !generation || !plan.valid)
            return false;
        D3DSURFACE_DESC desc{};
        Microsoft::WRL::ComPtr<IDirect3DDevice9> actualOwner;
        if (FAILED(backbuffer->GetDesc(&desc)) ||
            FAILED(backbuffer->GetDevice(actualOwner.GetAddressOf())) ||
            !actualOwner || actualOwner.Get() != game ||
            desc.Width != width || desc.Height != height ||
            desc.Format != format || desc.MultiSampleType != D3DMULTISAMPLE_NONE ||
            !plan.region.full_frame_placement(width,height,width,height).valid)
            return false;
        const UINT tileWidth = static_cast<UINT>(plan.region.right-plan.region.left);
        const UINT tileHeight = static_cast<UINT>(plan.region.bottom-plan.region.top);
        if (!backup_ || owner_.Get() != game ||
            width_ != width || height_ != height || generation_ != generation ||
            format_ != format || tileWidth_ != tileWidth ||
            tileHeight_ != tileHeight) {
            // No DEFAULT-pool reuse across source, Reset, resolution or generation.
            backup_.Reset(); owner_.Reset();
            if (FAILED(game->CreateRenderTarget(
                    tileWidth,tileHeight,format,D3DMULTISAMPLE_NONE,0u,FALSE,
                    backup_.GetAddressOf(),nullptr)) || !backup_)
                return false;
            owner_ = game;
            width_ = width; height_ = height;
            tileWidth_ = tileWidth; tileHeight_ = tileHeight;
            format_ = format; generation_ = generation;
        }
        const RECT affected{
            static_cast<LONG>(plan.region.left),
            static_cast<LONG>(plan.region.top),
            static_cast<LONG>(plan.region.right),
            static_cast<LONG>(plan.region.bottom)};
        // Snapshot first; failed snapshot performs no native upload.
        if (FAILED(game->StretchRect(
                backbuffer,&affected,backup_.Get(),nullptr,D3DTEXF_NONE)))
            return false;
        active_ = affected; armed_ = true;
        return true;
    }
    void commit() noexcept { armed_ = false; }
    [[nodiscard]] bool restore(IDirect3DDevice9* game,
                                IDirect3DSurface9* backbuffer) noexcept {
        if (!armed_ || !game || !backbuffer || !backup_ ||
            owner_.Get() != game) {
            faulted_ = true; armed_ = false;
            return false;
        }
        armed_ = false;
        if (FAILED(game->StretchRect(
                backup_.Get(),nullptr,backbuffer,&active_,D3DTEXF_NONE))) {
            // Partial fallback restoration failed: quarantine until output Reset.
            faulted_ = true;
            return false;
        }
        return true;
    }
private:
    Microsoft::WRL::ComPtr<IDirect3DSurface9> backup_;
    Microsoft::WRL::ComPtr<IDirect3DDevice9> owner_;
    std::uint32_t width_ = 0u, height_ = 0u;
    std::uint32_t tileWidth_ = 0u, tileHeight_ = 0u;
    std::uint64_t generation_ = 0u;
    D3DFORMAT format_ = D3DFMT_UNKNOWN;
    RECT active_{};
    bool armed_ = false, faulted_ = false;
};
} // namespace outrun::vr::dx11::live_game_frame
