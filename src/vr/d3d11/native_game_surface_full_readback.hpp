#pragma once
#include <Windows.h>
#include <d3d9.h>
#include <wrl/client.h>
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// Complete REAL game backbuffer readback if direct GetRenderTargetData is
// rejected by a D3D9 driver. Intermediate surface belongs to the exact
// D3D9 device/extent/format and is DEFAULT-pool; reset before game Reset.
// Caller authenticates the main backbuffer and charges the FULL readback
// budget before entering capture(). Neither path modifies game pixels.
class GameNativeFullSurfaceReadback final {
public:
    GameNativeFullSurfaceReadback() = default;
    GameNativeFullSurfaceReadback(const GameNativeFullSurfaceReadback&) = delete;
    GameNativeFullSurfaceReadback& operator=(const GameNativeFullSurfaceReadback&) = delete;
    void reset() noexcept {
        gpu_.Reset();
        owner_ = nullptr;
        width_ = height_ = 0u;
        format_ = D3DFMT_UNKNOWN;
    }
    [[nodiscard]] bool capture(IDirect3DDevice9* game,
        IDirect3DSurface9* source, IDirect3DSurface9* systemStaging,
        std::uint32_t width, std::uint32_t height,
        D3DFORMAT format) noexcept {
        if (!game || !source || !systemStaging || !width || !height ||
            (format != D3DFMT_A8R8G8B8 && format != D3DFMT_X8R8G8B8))
            return false;
        D3DSURFACE_DESC src{}, dst{};
        if (FAILED(source->GetDesc(&src)) ||
            FAILED(systemStaging->GetDesc(&dst)) ||
            src.Width != width || src.Height != height ||
            src.Format != format || src.Pool != D3DPOOL_DEFAULT ||
            src.MultiSampleType != D3DMULTISAMPLE_NONE ||
            dst.Width != width || dst.Height != height ||
            dst.Format != format || dst.Pool != D3DPOOL_SYSTEMMEM)
            return false;
        if (!gpu_ || owner_ != game || width_ != width ||
            height_ != height || format_ != format) {
            reset();
            if (FAILED(game->CreateRenderTarget(
                    width,height,format,D3DMULTISAMPLE_NONE,0u,FALSE,
                    gpu_.GetAddressOf(),nullptr)) || !gpu_) {
                reset();
                return false;
            }
            owner_ = game;
            width_ = width; height_ = height; format_ = format;
        }
        // This goes through the same game's hooked StretchRect, so the
        // bridge caller MUST hold NativeOutputUploadScope against recursion.
        // No viewport transform, resampling, or content substitution.
        if (FAILED(game->StretchRect(
                source,nullptr,gpu_.Get(),nullptr,D3DTEXF_NONE)))
            return false;
        return SUCCEEDED(game->GetRenderTargetData(
            gpu_.Get(),systemStaging));
    }
private:
    Microsoft::WRL::ComPtr<IDirect3DSurface9> gpu_;
    IDirect3DDevice9* owner_ = nullptr; // non-owning; invalidated on Reset
    std::uint32_t width_ = 0u, height_ = 0u;
    D3DFORMAT format_ = D3DFMT_UNKNOWN;
};
} // namespace outrun::vr::dx11::live_game_frame
