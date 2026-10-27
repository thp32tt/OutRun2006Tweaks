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

namespace outrun::vr::dx11 {
enum class NativeRawPreviewResult {
    NoDraw, CopyQueued, GpuPending, VisibleGpuPixels, NoChangedPixels,
    UnsafePresent, InvalidNativeColor, GpuFailure, UploadFailure
};
class NativeRawVisualPreview final {
public:
    static constexpr UINT width = 256, height = 144;
    void reset() noexcept {
        staging_.Reset(); event_.Reset(); surface_.Reset();
        gameOwner_ = nullptr; gpuOwner_ = nullptr; format_ = D3DFMT_UNKNOWN;
        pending_ = false; lastDraws_ = 0;
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
        const bool newDraw = draws > lastDraws_;
        lastDraws_ = draws;
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
                D3D11_MAPPED_SUBRESOURCE mapped{};
                const HRESULT hr = ctx->Map(staging_.Get(), 0,
                    D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
                if (hr == DXGI_ERROR_WAS_STILL_DRAWING)
                    return NativeRawPreviewResult::GpuPending;
                pending_ = false;
                if (hr != S_OK || !mapped.pData || mapped.RowPitch < width * 4u)
                    return NativeRawPreviewResult::GpuFailure;
                for (UINT y = 0; y < height; ++y) {
                    const auto* row = static_cast<const std::uint8_t*>(mapped.pData) +
                        static_cast<std::size_t>(y) * mapped.RowPitch;
                    for (UINT x = 0; x < width; ++x) {
                        const auto* p = row + 4u * x;
                        if (std::abs(int(p[0])-20)>3 || std::abs(int(p[1])-9)>3 ||
                            std::abs(int(p[2])-9)>3) ++nativePixels;
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
                    ctx->Unmap(staging_.Get(), 0);
                    const POINT destination{r-static_cast<LONG>(width)-8, t+8};
                    if (SUCCEEDED(unlocked) &&
                        SUCCEEDED(game->UpdateSurface(
                            surface_.Get(), nullptr, backbuffer, &destination)))
                        output = NativeRawPreviewResult::VisibleGpuPixels;
                    else output = NativeRawPreviewResult::UploadFailure;
                } else {
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
        if (!newDraw || pending_) return output;
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
        if (!staging_) {
            D3D11_TEXTURE2D_DESC dst{};
            dst.Width = width; dst.Height = height;
            dst.MipLevels = 1; dst.ArraySize = 1;
            dst.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
            dst.SampleDesc.Count = 1;
            dst.Usage = D3D11_USAGE_STAGING;
            dst.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
            if (FAILED(dev->CreateTexture2D(&dst, nullptr,
                                             staging_.GetAddressOf())))
                return NativeRawPreviewResult::GpuFailure;
        }
        if (!event_) {
            const D3D11_QUERY_DESC desc{D3D11_QUERY_EVENT, 0u};
            if (FAILED(dev->CreateQuery(&desc, event_.GetAddressOf())))
                return NativeRawPreviewResult::GpuFailure;
        }
        const UINT index = static_cast<UINT>(capture_++ % 5u);
        const UINT rangeX = src.Width - width, rangeY = src.Height - height;
        const UINT x = index == 0 ? rangeX/2u :
                       index == 1 || index == 3 ? 0u : rangeX;
        const UINT y = index == 0 ? rangeY/2u :
                       index == 1 || index == 2 ? 0u : rangeY;
        const D3D11_BOX region{x,y,0u,x+width,y+height,1u};
        ctx->CopySubresourceRegion(staging_.Get(), 0, 0, 0, 0, color, 0, &region);
        ctx->End(event_.Get());
        ctx->Flush();
        pending_ = true;
        return output == NativeRawPreviewResult::VisibleGpuPixels
            ? output : NativeRawPreviewResult::CopyQueued;
    }
private:
    Microsoft::WRL::ComPtr<ID3D11Texture2D> staging_;
    Microsoft::WRL::ComPtr<ID3D11Query> event_;
    Microsoft::WRL::ComPtr<IDirect3DSurface9> surface_;
    IDirect3DDevice9* gameOwner_ = nullptr;
    ID3D11Device* gpuOwner_ = nullptr;
    D3DFORMAT format_ = D3DFMT_UNKNOWN;
    std::uint64_t lastDraws_ = 0, capture_ = 0;
    bool pending_ = false;
};
} // namespace outrun::vr::dx11
