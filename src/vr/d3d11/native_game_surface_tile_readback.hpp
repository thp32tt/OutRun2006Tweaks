#pragma once
#include <Windows.h>
#include <d3d9.h>
#include <wrl/client.h>
#include <cstdint>
#include "native_game_surface_tile_plan.hpp"

namespace outrun::vr::dx11::live_game_frame {
// Read a real D3D9 post-Draw backbuffer TILE via a same-format GPU RT.
// The source D3D9 backbuffer is NEVER written; unsupported drivers may
// return failure and the caller then uses the original full readback.
// The DEFAULT-pool tile is released before the owning game device Reset.
class GameNativeSurfaceTileReadback final {
public:
    GameNativeSurfaceTileReadback() = default;
    GameNativeSurfaceTileReadback(const GameNativeSurfaceTileReadback&) = delete;
    GameNativeSurfaceTileReadback& operator=(const GameNativeSurfaceTileReadback&) = delete;
    void reset() noexcept {
        system_.Reset();
        gpu_.Reset();
        owner_ = nullptr;
        width_ = height_ = 0u;
        format_ = D3DFMT_UNKNOWN;
    }
    [[nodiscard]] IDirect3DSurface9* staging() const noexcept {
        return system_.Get();
    }
    [[nodiscard]] bool capture(IDirect3DDevice9* game,
        IDirect3DSurface9* source, GameNativeSurfaceCopyRegion r,
        std::uint32_t fullWidth, std::uint32_t fullHeight,
        D3DFORMAT format) noexcept {
        if (!game || !source || format == D3DFMT_UNKNOWN ||
            !GameNativeSurfaceTilePlan::eligible(r, fullWidth, fullHeight))
            return false;
        const UINT tileW = r.width(), tileH = r.height();
        if (!gpu_ || !system_ || owner_ != game ||
            width_ != tileW || height_ != tileH || format_ != format) {
            reset();
            // Matching, nonmultisampled RT only: no rescaling or filtering
            // of D3D9 menu/vehicle/HUD pixels into native output.
            if (FAILED(game->CreateRenderTarget(
                tileW, tileH, format, D3DMULTISAMPLE_NONE, 0u, FALSE,
                gpu_.GetAddressOf(), nullptr)) || !gpu_ ||
                FAILED(game->CreateOffscreenPlainSurface(
                tileW, tileH, format, D3DPOOL_SYSTEMMEM,
                system_.GetAddressOf(), nullptr)) || !system_) {
                reset();
                return false;
            }
            owner_ = game;
            width_ = tileW;
            height_ = tileH;
            format_ = format;
        }
        const RECT area{static_cast<LONG>(r.left),
                        static_cast<LONG>(r.top),
                        static_cast<LONG>(r.right),
                        static_cast<LONG>(r.bottom)};
        // StretchRect writes ONLY our private scratch surface. If D3D9
        // rejects this RT->RT copy, no source or native pixels were touched.
        return SUCCEEDED(game->StretchRect(
                source, &area, gpu_.Get(), nullptr, D3DTEXF_NONE)) &&
            SUCCEEDED(game->GetRenderTargetData(gpu_.Get(), system_.Get()));
    }
private:
    Microsoft::WRL::ComPtr<IDirect3DSurface9> gpu_;
    Microsoft::WRL::ComPtr<IDirect3DSurface9> system_;
    IDirect3DDevice9* owner_ = nullptr; // non-owning, guarded by game Reset
    UINT width_ = 0u, height_ = 0u;
    D3DFORMAT format_ = D3DFMT_UNKNOWN;
};
} // namespace outrun::vr::dx11::live_game_frame
