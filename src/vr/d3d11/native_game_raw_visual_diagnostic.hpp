#pragma once
// Explicitly opted-in D3D11 GPU pixel tile. It is NOT a native full frame,
// and the original D3D9 game and VR stereoscopy remain authoritative.
#include <d3d9.h>
#include <d3d11.h>
#include <dxgi.h>
#include <wrl/client.h>
#include <cmath>
#include <cstdint>
#include <cstring>
#include "native_game_raw_gpu_capture_epoch.hpp"
#include "native_game_raw_pixel_delta.hpp"
#include "native_game_raw_draw_tile.hpp"
#include "native_game_raw_draw_pair.hpp"

namespace outrun::vr::dx11 {
enum class NativeRawPreviewResult {
    NoDraw, CopyQueued, GpuPending, VisibleGpuPixels, NoChangedPixels,
    UnsafePresent, InvalidNativeColor, GpuFailure, UploadFailure
};
class NativeRawVisualPreview final {
public:
    static constexpr UINT width = 256, height = 144;
    void reset() noexcept {
        staging_.Reset(); baseline_.Reset(); event_.Reset(); surface_.Reset();
        drawPair_.reset();
        gameOwner_ = nullptr; gpuOwner_ = nullptr; format_ = D3DFMT_UNKNOWN;
        pending_ = false; lastDraws_ = 0;
        captureEpoch_.reset();
    }
    NativeRawPreviewResult present(
        IDirect3DDevice9* game, IDirect3DSurface9* backbuffer,
        const D3DSURFACE_DESC& back, const RECT* crop, bool dirty,
        ID3D11Device* dev, ID3D11DeviceContext* ctx, ID3D11Texture2D* color,
        std::uint64_t draws, UINT& nativePixels) noexcept {
        nativePixels = 0;
        if (!game || !backbuffer || !dev || !ctx || !color)
            return NativeRawPreviewResult::UnsafePresent;
        if (gameOwner_ != game || gpuOwner_ != dev) {
            reset(); gameOwner_ = game; gpuOwner_ = dev;
        }
        lastDraws_ = draws;
        (void)captureEpoch_.consume();
        const LONG l = crop ? crop->left : 0, t = crop ? crop->top : 0;
        const LONG r = crop ? crop->right : static_cast<LONG>(back.Width);
        const LONG b = crop ? crop->bottom : static_cast<LONG>(back.Height);
        if (dirty || ctx->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
            back.MultiSampleType != D3DMULTISAMPLE_NONE ||
            (back.Format != D3DFMT_A8R8G8B8 &&
             back.Format != D3DFMT_X8R8G8B8) ||
            l < 0 || t < 0 || r > static_cast<LONG>(back.Width) ||
            b > static_cast<LONG>(back.Height) ||
            r - l < static_cast<LONG>(width + 16) ||
            b - t < static_cast<LONG>(height + 16))
            return NativeRawPreviewResult::UnsafePresent;
        NativeRawPreviewResult output = NativeRawPreviewResult::NoDraw;
        if (pending_) {
            const HRESULT done = ctx->GetData(
                event_.Get(), nullptr, 0, D3D11_ASYNC_GETDATA_DONOTFLUSH);
            if (done == S_OK) {
                // Only a paired pre-Draw and post-Draw copy is GPU pixel
                // evidence. A static clear or last frame's pixels is not.
                D3D11_MAPPED_SUBRESOURCE before{}, mapped{};
                const HRESULT beforeHr = ctx->Map(baseline_.Get(), 0,
                    D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &before);
                if (beforeHr == DXGI_ERROR_WAS_STILL_DRAWING)
                    return NativeRawPreviewResult::GpuPending;
                if (beforeHr != S_OK || !before.pData ||
                    before.RowPitch < width * 4u) {
                    if (beforeHr == S_OK) ctx->Unmap(baseline_.Get(), 0);
                    pending_ = false;
                    return NativeRawPreviewResult::GpuFailure;
                }
                const HRESULT hr = ctx->Map(staging_.Get(), 0,
                    D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
                if (hr == DXGI_ERROR_WAS_STILL_DRAWING) {
                    ctx->Unmap(baseline_.Get(), 0);
                    return NativeRawPreviewResult::GpuPending;
                }
                pending_ = false;
                if (hr != S_OK || !mapped.pData || mapped.RowPitch < width * 4u) {
                    if (hr == S_OK) ctx->Unmap(staging_.Get(), 0);
                    ctx->Unmap(baseline_.Get(), 0);
                    return NativeRawPreviewResult::GpuFailure;
                }
                for (UINT y = 0; y < height; ++y) {
                    const auto* afterRow = static_cast<const std::uint8_t*>(mapped.pData) +
                        static_cast<std::size_t>(y) * mapped.RowPitch;
                    const auto* beforeRow = static_cast<const std::uint8_t*>(before.pData) +
                        static_cast<std::size_t>(y) * before.RowPitch;
                    for (UINT x = 0; x < width; ++x) {
                        if (native_raw_rgb_changed(beforeRow + 4u * x,
                                                   afterRow + 4u * x))
                            ++nativePixels;
                    }
                }
                if (nativePixels) {
                    if (!surface_ || format_ != back.Format) {
                        surface_.Reset();
                        format_ = D3DFMT_UNKNOWN;
                        if (SUCCEEDED(game->CreateOffscreenPlainSurface(
                                width, height, back.Format, D3DPOOL_SYSTEMMEM,
                                surface_.GetAddressOf(), nullptr)))
                            format_ = back.Format;
                    }
                    D3DLOCKED_RECT locked{};
                    if (!surface_ || FAILED(surface_->LockRect(&locked, nullptr, 0))) {
                        ctx->Unmap(baseline_.Get(), 0);
                        ctx->Unmap(staging_.Get(), 0);
                        return NativeRawPreviewResult::UploadFailure;
                    }
                    for (UINT y = 0; y < height; ++y) {
                        const auto* src = static_cast<const std::uint8_t*>(mapped.pData) +
                            static_cast<std::size_t>(y) * mapped.RowPitch;
                        auto* dst = static_cast<std::uint8_t*>(locked.pBits) +
                            static_cast<std::size_t>(y) * locked.Pitch;
                        std::memcpy(dst, src, width * 4u);
                        // Unmistakable magenta INCOMPLETE GPU tile border.
                        for (UINT x = 0; x < width; ++x) {
                            if (x < 3 || x >= width-3 || y < 4 || y >= height-4) {
                                dst[x*4u] = 255; dst[x*4u+1u] = 0;
                                dst[x*4u+2u] = 255;
                            }
                            if (back.Format == D3DFMT_X8R8G8B8)
                                dst[x*4u+3u] = 255;
                        }
                    }
                    const HRESULT unlocked = surface_->UnlockRect();
                    ctx->Unmap(baseline_.Get(), 0);
                        ctx->Unmap(staging_.Get(), 0);
                    const POINT destination{r-static_cast<LONG>(width)-8, t+8};
                    if (SUCCEEDED(unlocked) &&
                        SUCCEEDED(game->UpdateSurface(
                            surface_.Get(), nullptr, backbuffer, &destination)))
                        output = NativeRawPreviewResult::VisibleGpuPixels;
                    else output = NativeRawPreviewResult::UploadFailure;
                } else {
                    ctx->Unmap(baseline_.Get(), 0);
                        ctx->Unmap(staging_.Get(), 0);
                    output = NativeRawPreviewResult::NoChangedPixels;
                }
            } else if (done == S_FALSE) {
                return NativeRawPreviewResult::GpuPending;
            } else {
                pending_ = false;
                return NativeRawPreviewResult::GpuFailure;
            }
        }
        // Never infer a new GPU pixel from the post-Draw texture alone:
        // a clear or earlier native Draw may already have colored the region.
        // Discard any unpaired pre-copy (e.g. an aborted source submission).
        drawPair_.reset();
        return output;
    }
    void begin_real_native_draw(
        IDirect3DDevice9* game, ID3D11Device* dev,
        ID3D11DeviceContext* ctx, ID3D11Texture2D* color,
        std::uint64_t presentingSerial) noexcept {
        if (!game || !dev || !ctx || !color ||
            ctx->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE) return;
        if (gameOwner_ != game || gpuOwner_ != dev) {
            reset(); gameOwner_ = game; gpuOwner_ = dev;
        }
        // One source-owned pair per frame; a GPU event still in flight blocks
        // allocation/reuse of BOTH before/after staging resources.
        // A previous source Draw can fail *after* its BEFORE copy. Discard
        // the unpaired capture before selecting a new genuine source Draw,
        // or a later POST copy could falsely inherit the old baseline.
        drawPair_.reset();
        if (!captureEpoch_.can_queue(presentingSerial, pending_))
            return;
        if (queue_before_draw(dev, ctx, color) == NativeRawPreviewResult::CopyQueued)
            drawPair_.arm(presentingSerial, color);
    }
    void abort_real_native_draw() noexcept { drawPair_.reset(); }
    [[nodiscard]] bool sample_real_native_draw(
        IDirect3DDevice9* game, ID3D11Device* dev,
        ID3D11DeviceContext* ctx, ID3D11Texture2D* color,
        std::uint64_t presentingSerial) noexcept {
        // Consume the source token exactly once, even on an invalid device.
        // Never attribute pixels from a failed Draw to a later Draw.
        if (!drawPair_.consume(presentingSerial, color) ||
            !game || game != gameOwner_ || dev != gpuOwner_ ||
            !ctx || !color ||
            ctx->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
            pending_) return false;
        // D3D11 immediate-context order guarantees this GPU copy follows
        // exactly the original game's native Draw(s). The paired BEFORE copy
        // preceded that draw, using the identical, source-owned GPU box.
        ctx->CopySubresourceRegion(staging_.Get(), 0, 0, 0, 0,
                                   color, 0, &region_);
        ctx->End(event_.Get());
        ctx->Flush();
        pending_ = true;
        captureEpoch_.queued(presentingSerial);
        return true;
    }
private:
    NativeRawPreviewResult queue_before_draw(
        ID3D11Device* dev, ID3D11DeviceContext* ctx,
        ID3D11Texture2D* color) noexcept {
        if (!dev || !ctx || !color || pending_)
            return NativeRawPreviewResult::GpuFailure;
        D3D11_TEXTURE2D_DESC src{};
        color->GetDesc(&src);
        Microsoft::WRL::ComPtr<ID3D11Device> actual;
        color->GetDevice(actual.GetAddressOf());
        if (actual.Get() != dev || src.Width < width || src.Height < height ||
            src.ArraySize != 1u || src.MipLevels != 1u ||
            src.SampleDesc.Count != 1u || src.Usage != D3D11_USAGE_DEFAULT ||
            src.CPUAccessFlags || !(src.BindFlags & D3D11_BIND_RENDER_TARGET) ||
            (src.Format != DXGI_FORMAT_B8G8R8A8_UNORM &&
             src.Format != DXGI_FORMAT_B8G8R8A8_TYPELESS))
            return NativeRawPreviewResult::InvalidNativeColor;
        if (!staging_ || !baseline_) {
            D3D11_TEXTURE2D_DESC dst{};
            dst.Width = width; dst.Height = height;
            dst.MipLevels = 1; dst.ArraySize = 1;
            dst.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
            dst.SampleDesc.Count = 1;
            dst.Usage = D3D11_USAGE_STAGING;
            dst.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
            if (!staging_ && FAILED(dev->CreateTexture2D(
                    &dst, nullptr, staging_.GetAddressOf())))
                return NativeRawPreviewResult::GpuFailure;
            if (!baseline_ && FAILED(dev->CreateTexture2D(
                    &dst, nullptr, baseline_.GetAddressOf())))
                return NativeRawPreviewResult::GpuFailure;
        }
        if (!event_) {
            const D3D11_QUERY_DESC desc{D3D11_QUERY_EVENT, 0u};
            if (FAILED(dev->CreateQuery(&desc, event_.GetAddressOf())))
                return NativeRawPreviewResult::GpuFailure;
        }
        // Capture the actual bound native Draw viewport/scissor, not a
        // whole-backbuffer anchor that can miss game menu/HUD raster output.
        UINT viewCount=1u;
        D3D11_VIEWPORT view{};
        ctx->RSGetViewports(&viewCount,&view);
        const float right=view.TopLeftX+view.Width;
        const float bottom=view.TopLeftY+view.Height;
        if(viewCount!=1u||!std::isfinite(view.TopLeftX)||
           !std::isfinite(view.TopLeftY)||!std::isfinite(view.Width)||
           !std::isfinite(view.Height)||!std::isfinite(right)||
           !std::isfinite(bottom)||view.Width<=0.f||view.Height<=0.f)
            return NativeRawPreviewResult::NoDraw;
        const auto clip=[](float value,UINT limit) noexcept {
            return static_cast<std::int64_t>((std::max)(0.f,
                (std::min)(value,static_cast<float>(limit))));
        };
        NativeRawDrawExtent draw{clip(view.TopLeftX,src.Width),
            clip(view.TopLeftY,src.Height),clip(right,src.Width),
            clip(bottom,src.Height)};
        Microsoft::WRL::ComPtr<ID3D11RasterizerState> raster;
        ctx->RSGetState(raster.GetAddressOf());
        if(raster){
            D3D11_RASTERIZER_DESC desc{};
            raster->GetDesc(&desc);
            if(desc.ScissorEnable){
                UINT count=1u;
                D3D11_RECT rect{};
                ctx->RSGetScissorRects(&count,&rect);
                if(count!=1u) return NativeRawPreviewResult::NoDraw;
                draw.left=(std::max)(draw.left,std::int64_t{rect.left});
                draw.top=(std::max)(draw.top,std::int64_t{rect.top});
                draw.right=(std::min)(draw.right,std::int64_t{rect.right});
                draw.bottom=(std::min)(draw.bottom,std::int64_t{rect.bottom});
            }
        }
        NativeRawTileOrigin tile{};
        if(!native_raw_draw_tile(src.Width,src.Height,width,height,
                                 draw,static_cast<std::uint32_t>(capture_),tile))
            return NativeRawPreviewResult::NoDraw;
        ++capture_;
        region_=D3D11_BOX{tile.x,tile.y,0u,
                          tile.x+width,tile.y+height,1u};
        ctx->CopySubresourceRegion(baseline_.Get(), 0, 0, 0, 0,
                                   color, 0, &region_);
        return NativeRawPreviewResult::CopyQueued;
    }
    Microsoft::WRL::ComPtr<ID3D11Texture2D> staging_, baseline_;
    D3D11_BOX region_{};
    NativeRawDrawPair drawPair_{};
    Microsoft::WRL::ComPtr<ID3D11Query> event_;
    Microsoft::WRL::ComPtr<IDirect3DSurface9> surface_;
    IDirect3DDevice9* gameOwner_ = nullptr;
    ID3D11Device* gpuOwner_ = nullptr;
    D3DFORMAT format_ = D3DFMT_UNKNOWN;
    std::uint64_t lastDraws_ = 0, capture_ = 0;
    bool pending_ = false;
    NativeRawGpuCaptureEpoch captureEpoch_{};
};
} // namespace outrun::vr::dx11
