#pragma once
// Explicitly opted-in D3D11 GPU pixel tile. It is NOT a native full frame,
// and the original D3D9 game and VR stereoscopy remain authoritative.
#include <d3d9.h>
#include <d3d11.h>
#include <dxgi.h>
#include <wrl/client.h>
#include <cmath>
#include <chrono>
#include <thread>
#include <cstdint>
#include <cstring>
#include <limits>
#include "native_game_raw_gpu_capture_epoch.hpp"
#include "native_game_raw_pixel_delta.hpp"
#include "native_game_raw_draw_tile.hpp"
#include "native_game_raw_dual_tile.hpp"
#include "native_game_raw_draw_pair.hpp"
#include "native_game_raw_partial_present_tile.hpp"
#include "native_game_raw_changed_pixel_window.hpp"
#include "native_game_raw_gpu_wait.hpp"

namespace outrun::vr::dx11 {
enum class NativeRawPreviewResult {
    NoDraw, CopyQueued, GpuPending, VisibleGpuPixels, NoChangedPixels,
    UnsafePresent, InvalidNativeColor, GpuFailure, UploadFailure,
    StaleGpuCopy
};
class NativeRawVisualPreview final {
public:
    static constexpr UINT width = 256, height = 144;
    void reset() noexcept {
        staging_.Reset(); baseline_.Reset();
        stagingAlternate_.Reset(); baselineAlternate_.Reset();
        surfaceAlternate_.Reset();
        event_.Reset(); surface_.Reset();
        drawPair_.reset(); region_ = {}; regionAlternate_ = {};
        alternateActive_ = false;
        gameOwner_ = nullptr; gpuOwner_ = nullptr; format_ = D3DFMT_UNKNOWN;
        pending_ = false; quarantined_ = false; lastDraws_ = 0;
        recoveredLateCopies_ = 0u;
        zeroRgbRetiredCopies_ = 0u; zeroRgbRearmsThisPresent_ = 0u;
        rearmSerial_ = (std::numeric_limits<std::uint64_t>::max)();
        rgbEvidenceConfirmed_ = false;
        captureEpoch_.reset();
    }
    [[nodiscard]] std::uint64_t recovered_late_copies() const noexcept {
        return recoveredLateCopies_;
    }
    [[nodiscard]] std::uint64_t zero_rgb_retired_copies() const noexcept {
        return zeroRgbRetiredCopies_;
    }
    // Whole AND clipped source-backbuffer TARGET Clears supersede a queued
    // native RGB sample. A foreign D3D9 device cannot retire its GPU copy;
    // in-flight staging remains owned by the original EVENT fence.
    [[nodiscard]] bool invalidate_source_color_write(
        IDirect3DDevice9* game,
        const NativeRawSourcePixelRect* changedRects = nullptr,
        std::uint32_t changedCount = 0u) noexcept {
        if (!game || gameOwner_ != game) return false;
        // The GPU capture is a 256x144 source-authentic tile, not the
        // complete D3D9 scene. An explicitly bounded disjoint color write
        // elsewhere cannot supersede these pixels. Unknown/full writes still
        // invalidate conservatively. Never release an in-flight GPU EVENT.
        // Either of the two GPU-authentic RGB regions can be superseded by
        // an original D3D9 color write. A write touching only the SECOND
        // tile must also revoke both pairs: we cannot expose stale pixels.
        if (!native_raw_dual_source_write_overlaps(
                region_.left, region_.top, alternateActive_,
                regionAlternate_.left, regionAlternate_.top,
                width, height, changedRects, changedCount))
            return false;
        drawPair_.reset();
        rgbEvidenceConfirmed_ = false;
        return captureEpoch_.invalidate_for_full_source_clear(pending_);
    }
    [[nodiscard]] bool invalidate_source_target_clear(
        IDirect3DDevice9* game,
        const NativeRawSourcePixelRect* changedRects = nullptr,
        std::uint32_t changedCount = 0u) noexcept {
        return invalidate_source_color_write(game, changedRects, changedCount);
    }
    NativeRawPreviewResult present(
        IDirect3DDevice9* game, IDirect3DSurface9* backbuffer,
        const D3DSURFACE_DESC& back, const RECT* crop,
        bool sourceCropRepaintVerified,
        const NativeRawPresentDirtyRegion* sourceDirty,
        ID3D11Device* dev, ID3D11DeviceContext* ctx, ID3D11Texture2D* color,
        std::uint64_t draws, std::uint64_t presentingSerial,
        UINT& nativePixels) noexcept {
        nativePixels = 0;
        if (!game || !backbuffer || !dev || !ctx || !color)
            return NativeRawPreviewResult::UnsafePresent;
        if (gameOwner_ != game || gpuOwner_ != dev) {
            reset(); gameOwner_ = game; gpuOwner_ = dev;
        }
        lastDraws_ = draws;
        // A timeout preserves staging ownership but not permission to paint
        // the subsequent D3D9 Present with the earlier Draw's GPU result.
        const bool matchingPresent = captureEpoch_.consume_for_present(
            presentingSerial);
        const LONG l = crop ? crop->left : 0, t = crop ? crop->top : 0;
        const LONG r = crop ? crop->right : static_cast<LONG>(back.Width);
        const LONG b = crop ? crop->bottom : static_cast<LONG>(back.Height);
        if ((!sourceCropRepaintVerified && !sourceDirty) ||
            ctx->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
            back.MultiSampleType != D3DMULTISAMPLE_NONE ||
            (back.Format != D3DFMT_A8R8G8B8 &&
             back.Format != D3DFMT_X8R8G8B8) ||
            l < 0 || t < 0 || r > static_cast<LONG>(back.Width) ||
            b > static_cast<LONG>(back.Height) ||
            l >= r || t >= b)
            return NativeRawPreviewResult::UnsafePresent;
        NativeRawPresentTile visibleTile{};
        if (!native_raw_partial_present_tile(
                back.Width, back.Height, l, t, r, b,
                width, height, visibleTile))
            return NativeRawPreviewResult::UnsafePresent;
        NativeRawPreviewResult output = NativeRawPreviewResult::NoDraw;
        if (pending_) {
            // RAW is an explicitly opted-in visual test. Prefer the SAME
            // original game's Present epoch over presenting a late GPU tile
            // on an unrelated following frame. The producer already Flush()ed
            // its source-ordered BEFORE/Draw/AFTER/event sequence.
            // Wait is strictly bounded: a busy or lost GPU never stalls DX9Ex.
            const auto waitStart = std::chrono::steady_clock::now();
            const auto done = native_raw_wait_gpu_copy(
                [&]() noexcept {
                    const HRESULT hr = ctx->GetData(event_.Get(), nullptr, 0,
                        D3D11_ASYNC_GETDATA_DONOTFLUSH);
                    return hr == S_OK ? NativeRawGpuWaitResult::Complete :
                           hr == S_FALSE ? NativeRawGpuWaitResult::Pending :
                                           NativeRawGpuWaitResult::Failed;
                },
                [&]() noexcept -> std::uint64_t {
                    return static_cast<std::uint64_t>(
                        std::chrono::duration_cast<std::chrono::microseconds>(
                            std::chrono::steady_clock::now() - waitStart).count());
                },
                []() noexcept { std::this_thread::yield(); },
                24000u);
            if (done == NativeRawGpuWaitResult::Complete) {
                if (!matchingPresent) {
                    // Retire finished GPU staging without any CPU Map or
                    // UpdateSurface: this is an older game's source frame.
                    pending_ = false;
                    drawPair_.reset();
                    return NativeRawPreviewResult::StaleGpuCopy;
                }
                // Only a paired pre-Draw and post-Draw copy is GPU pixel
                // evidence. A static clear or last frame's pixels is not.
                D3D11_MAPPED_SUBRESOURCE before{}, mapped{};
                // Event completion orders BOTH staging copies after the
                // genuine native Draw. Map may therefore wait for completed
                // readback without losing the current D3D9 Present epoch.
                const HRESULT beforeHr = ctx->Map(baseline_.Get(), 0,
                    D3D11_MAP_READ, 0u, &before);
                if (beforeHr != S_OK || !before.pData ||
                    before.RowPitch < width * 4u) {
                    if (beforeHr == S_OK) ctx->Unmap(baseline_.Get(), 0);
                    pending_ = false;
                    quarantined_ = true; // invalid GPU Map needs Reset
                    return NativeRawPreviewResult::GpuFailure;
                }
                const HRESULT hr = ctx->Map(staging_.Get(), 0,
                    D3D11_MAP_READ, 0u, &mapped);
                pending_ = false;
                if (hr != S_OK || !mapped.pData || mapped.RowPitch < width * 4u) {
                    quarantined_ = true;
                    if (hr == S_OK) ctx->Unmap(staging_.Get(), 0);
                    ctx->Unmap(baseline_.Get(), 0);
                    return NativeRawPreviewResult::GpuFailure;
                }
                // Both authenticated source Draw regions share one GPU EVENT.
                // Never show pixels from a different Present or unsafe Map.
                D3D11_MAPPED_SUBRESOURCE beforeAlternate{}, afterAlternate{};
                if (alternateActive_) {
                    const HRESULT a = ctx->Map(baselineAlternate_.Get(), 0,
                        D3D11_MAP_READ, 0u, &beforeAlternate);
                    if (a != S_OK || !beforeAlternate.pData ||
                        beforeAlternate.RowPitch < width * 4u) {
                        if (a == S_OK) ctx->Unmap(baselineAlternate_.Get(), 0);
                        ctx->Unmap(baseline_.Get(), 0);
                        ctx->Unmap(staging_.Get(), 0);
                        quarantined_ = true;
                        return NativeRawPreviewResult::GpuFailure;
                    }
                    const HRESULT b = ctx->Map(stagingAlternate_.Get(), 0,
                        D3D11_MAP_READ, 0u, &afterAlternate);
                    if (b != S_OK || !afterAlternate.pData ||
                        afterAlternate.RowPitch < width * 4u) {
                        if (b == S_OK) ctx->Unmap(stagingAlternate_.Get(), 0);
                        ctx->Unmap(baselineAlternate_.Get(), 0);
                        ctx->Unmap(baseline_.Get(), 0);
                        ctx->Unmap(staging_.Get(), 0);
                        quarantined_ = true;
                        return NativeRawPreviewResult::GpuFailure;
                    }
                }
                const auto unmapPairs = [&]() noexcept {
                    if (alternateActive_) {
                        ctx->Unmap(stagingAlternate_.Get(), 0);
                        ctx->Unmap(baselineAlternate_.Get(), 0);
                    }
                    ctx->Unmap(staging_.Get(), 0);
                    ctx->Unmap(baseline_.Get(), 0);
                };
                // These are TWO independent, authentic GPU Draw regions. A
                // genuine RGB contribution in the second region must not be
                // lost simply because the first one was denser. Present both
                // as explicitly INCOMPLETE, disjoint RAW-only diagnostics
                // when the source crop accommodates them; otherwise choose
                // the strongest single genuine RGB region as before.
                const NativeRawPresentTile originalTile = visibleTile;
                NativeRawPresentTile firstTile{}, secondTile{};
                UINT firstPixels = 0u, secondPixels = 0u;
                changedWindow_.capture(before.pData, before.RowPitch,
                                       mapped.pData, mapped.RowPitch);
                if (!changedWindow_.select(originalTile, firstTile,
                                           firstPixels)) {
                    unmapPairs();
                    return NativeRawPreviewResult::UnsafePresent;
                }
                if (alternateActive_) {
                    changedWindow_.capture(beforeAlternate.pData,
                        beforeAlternate.RowPitch, afterAlternate.pData,
                        afterAlternate.RowPitch);
                    if (!changedWindow_.select(originalTile, secondTile,
                                               secondPixels)) {
                        unmapPairs();
                        quarantined_ = true;
                        return NativeRawPreviewResult::GpuFailure;
                    }
                }
                NativeRawPresentTile secondaryPlacement{};
                const bool canShowBoth = alternateActive_ && firstPixels &&
                    secondPixels && native_raw_secondary_present_tile(
                        originalTile, l, t, r, b, secondaryPlacement);
                if (canShowBoth) {
                    secondTile.destinationX = secondaryPlacement.destinationX;
                    secondTile.destinationY = secondaryPlacement.destinationY;
                }
                // Use original D3D9 dirty geometry rather than a broad rcBound
                // as visibility evidence. Menu and vehicle Presents can dirty
                // only one real GPU diagnostic tile; paint just that tile.
                const auto covered = [&](const NativeRawPresentTile& tile) noexcept {
                    return sourceCropRepaintVerified ||
                        (sourceDirty && native_raw_dirty_region_covers_tile(
                            back.Width, back.Height, *sourceDirty, tile));
                };
                const bool firstVisible = firstPixels && covered(firstTile);
                const bool secondVisible = alternateActive_ && secondPixels &&
                    covered(secondTile);
                if (!firstVisible && !secondVisible) {
                    unmapPairs();
                    return NativeRawPreviewResult::UnsafePresent;
                }
                if (format_ != back.Format) {
                    surface_.Reset();
                    surfaceAlternate_.Reset();
                    format_ = back.Format;
                }
                // Each region owns a distinct SYSTEMMEM staging surface. The
                // game driver may queue UpdateSurface, so never reuse or
                // overwrite the first surface while painting the second.
                const auto paint = [&](Microsoft::WRL::ComPtr<IDirect3DSurface9>& target,
                        const D3D11_MAPPED_SUBRESOURCE& prior,
                        const D3D11_MAPPED_SUBRESOURCE& after,
                        const NativeRawPresentTile& tile) noexcept -> bool {
                    if (!target && FAILED(game->CreateOffscreenPlainSurface(
                            width, height, back.Format, D3DPOOL_SYSTEMMEM,
                            target.GetAddressOf(), nullptr)))
                        return false;
                    D3DLOCKED_RECT locked{};
                    if (FAILED(target->LockRect(&locked, nullptr, 0)))
                        return false;
                    if (!locked.pBits || locked.Pitch < static_cast<INT>(width * 4u)) {
                        target->UnlockRect();
                        return false;
                    }
                    const auto* prev = static_cast<const std::uint8_t*>(prior.pData);
                    const auto* next = static_cast<const std::uint8_t*>(after.pData);
                    auto* dstBase = static_cast<std::uint8_t*>(locked.pBits);
                    for (UINT y = 0; y < height; ++y) {
                        const auto* p = prev + std::size_t{y} * prior.RowPitch;
                        const auto* src = next + std::size_t{y} * after.RowPitch;
                        auto* dst = dstBase + std::size_t{y} *
                            static_cast<std::size_t>(locked.Pitch);
                        std::memcpy(dst, src, width * 4u);
                        // A magenta RAW border may never hide a real RGB
                        // pixel at that border in either GPU source region.
                        for (UINT x = 0; x < width; ++x) {
                            if (native_raw_present_border_pixel(
                                    tile, x, y,
                                    native_raw_rgb_changed(p + 4u * x,
                                                           src + 4u * x))) {
                                dst[x * 4u] = 255u;
                                dst[x * 4u + 1u] = 0u;
                                dst[x * 4u + 2u] = 255u;
                            }
                            if (back.Format == D3DFMT_X8R8G8B8)
                                dst[x * 4u + 3u] = 255u;
                        }
                    }
                    const HRESULT unlockHr = target->UnlockRect();
                    if (FAILED(unlockHr)) return false;
                    const RECT srcRect{
                        static_cast<LONG>(tile.sourceX),
                        static_cast<LONG>(tile.sourceY),
                        static_cast<LONG>(tile.sourceX + tile.copyWidth),
                        static_cast<LONG>(tile.sourceY + tile.copyHeight)};
                    const POINT dstPoint{
                        static_cast<LONG>(tile.destinationX),
                        static_cast<LONG>(tile.destinationY)};
                    return SUCCEEDED(game->UpdateSurface(
                        target.Get(), &srcRect, backbuffer, &dstPoint));
                };
                if (canShowBoth && firstVisible && secondVisible) {
                    if (paint(surface_, before, mapped, firstTile))
                        nativePixels += firstPixels;
                    if (paint(surfaceAlternate_, beforeAlternate,
                              afterAlternate, secondTile))
                        nativePixels += secondPixels;
                } else if (secondVisible &&
                           (!firstVisible || native_raw_choose_second_tile(
                               firstPixels, secondPixels, true))) {
                    if (paint(surface_, beforeAlternate, afterAlternate, secondTile))
                        nativePixels = secondPixels;
                } else if (firstVisible) {
                    if (paint(surface_, before, mapped, firstTile))
                        nativePixels = firstPixels;
                }
                unmapPairs();
                output = nativePixels
                    ? NativeRawPreviewResult::VisibleGpuPixels
                    : (firstPixels || secondPixels)
                        ? NativeRawPreviewResult::UploadFailure
                        : NativeRawPreviewResult::NoChangedPixels;
            } else if (done == NativeRawGpuWaitResult::Pending) {
                return NativeRawPreviewResult::GpuPending;
            } else {
                pending_ = false;
                quarantined_ = true; // GPU/query failure needs Reset
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
        if (rearmSerial_ != presentingSerial) {
            rearmSerial_ = presentingSerial;
            zeroRgbRearmsThisPresent_ = 0u;
        }
        // A cropped/dirty/incompatible D3D9 Present may never enter present(),
        // leaving an orphaned GPU staging pair across menus/car/race frames.
        // Recover on a later genuine source Draw, with NO Map/UpdateSurface
        // of stale pixels. Only S_OK releases both textures for reuse;
        // S_FALSE holds the fence and any GPU failure quarantines until Reset.
        if (pending_ && captureEpoch_.previous_present_copy(presentingSerial)) {
            const auto retired = captureEpoch_.retire_previous_copy(
                presentingSerial, pending_, [&]() noexcept {
                    if (!event_) return NativeRawGpuWaitResult::Failed;
                    const HRESULT hr = ctx->GetData(event_.Get(), nullptr, 0,
                        D3D11_ASYNC_GETDATA_DONOTFLUSH);
                    return hr == S_OK ? NativeRawGpuWaitResult::Complete :
                           hr == S_FALSE ? NativeRawGpuWaitResult::Pending :
                                           NativeRawGpuWaitResult::Failed;
                });
            if (retired == NativeRawGpuWaitResult::Complete) {
                pending_ = false;
                ++recoveredLateCopies_;
            } else if (retired == NativeRawGpuWaitResult::Failed) {
                pending_ = false;
                quarantined_ = true;
            }
        }
        if (quarantined_) return;
        // Reclaim a superseded SAME-Present staging pair only after event
        // completion. Unknown/busy GPU results remain fail-closed.
        if (pending_ && captureEpoch_.invalidated_for_full_source_clear()) {
            const auto retired = captureEpoch_.retire_invalidated_source_clear(
                pending_, [&]() noexcept {
                    if (!event_) return NativeRawGpuWaitResult::Failed;
                    const HRESULT hr = ctx->GetData(event_.Get(), nullptr, 0,
                        D3D11_ASYNC_GETDATA_DONOTFLUSH);
                    return hr == S_OK ? NativeRawGpuWaitResult::Complete :
                           hr == S_FALSE ? NativeRawGpuWaitResult::Pending :
                                           NativeRawGpuWaitResult::Failed;
                });
            if (retired == NativeRawGpuWaitResult::Complete)
                pending_ = false;
            else if (retired == NativeRawGpuWaitResult::Failed) {
                pending_ = false;
                quarantined_ = true;
            }
        }
        if (quarantined_) return;
        // The first authentic native Draw may modify depth/alpha only.
        // Once its EVENT completes, abandon an RGB-inert copy and admit a
        // later real game Draw in THIS Present. Keep any RGB-positive pair.
        if (pending_ && !captureEpoch_.previous_present_copy(presentingSerial) &&
            !captureEpoch_.invalidated_for_full_source_clear())
            retire_same_present_zero_rgb_capture(ctx, presentingSerial);
        if (quarantined_) return;
        // One source-owned pair per frame; a GPU event still in flight blocks
        // allocation/reuse of BOTH before/after staging resources.
        // A previous source Draw can fail *after* its BEFORE copy. Discard
        // the unpaired capture before selecting a new genuine source Draw,
        // or a later POST copy could falsely inherit the old baseline.
        drawPair_.reset();
        if (!captureEpoch_.can_queue(presentingSerial, pending_))
            return;
        if (queue_before_draw(dev, ctx, color) == NativeRawPreviewResult::CopyQueued) {
            rgbEvidenceConfirmed_ = false;
            drawPair_.arm(presentingSerial, color);
        }
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
        if (alternateActive_)
            ctx->CopySubresourceRegion(stagingAlternate_.Get(), 0, 0, 0, 0,
                                       color, 0, &regionAlternate_);
        ctx->End(event_.Get());
        ctx->Flush();
        pending_ = true;
        captureEpoch_.queued(presentingSerial);
        return true;
    }
private:
    void retire_same_present_zero_rgb_capture(
        ID3D11DeviceContext* ctx, std::uint64_t presentSerial) noexcept {
        // Bound the extra readbacks: three different native GPU Draws at most
        // per original game Present. Never retry a positive RGB capture.
        if (!ctx || !pending_ || rgbEvidenceConfirmed_ ||
            zeroRgbRearmsThisPresent_ >= 2u || !event_ ||
            !baseline_ || !staging_) return;
        const HRESULT ready = ctx->GetData(event_.Get(), nullptr, 0,
            D3D11_ASYNC_GETDATA_DONOTFLUSH);
        if (ready == S_FALSE) return; // the GPU owns both staging images
        if (ready != S_OK) {
            pending_ = false; quarantined_ = true;
            return;
        }
        D3D11_MAPPED_SUBRESOURCE before{}, after{};
        const HRESULT beforeHr = ctx->Map(baseline_.Get(), 0,
            D3D11_MAP_READ, 0u, &before);
        if (beforeHr != S_OK || !before.pData ||
            before.RowPitch < width * 4u) {
            if (beforeHr == S_OK) ctx->Unmap(baseline_.Get(), 0);
            pending_ = false; quarantined_ = true;
            return;
        }
        const HRESULT afterHr = ctx->Map(staging_.Get(), 0,
            D3D11_MAP_READ, 0u, &after);
        if (afterHr != S_OK || !after.pData ||
            after.RowPitch < width * 4u) {
            if (afterHr == S_OK) ctx->Unmap(staging_.Get(), 0);
            ctx->Unmap(baseline_.Get(), 0);
            pending_ = false; quarantined_ = true;
            return;
        }
        bool changed = false;
        const bool valid = native_raw_has_rgb_delta(
            before.pData, before.RowPitch, after.pData, after.RowPitch,
            width, height, changed);
        bool alternateValid = true, alternateChanged = false;
        if (valid && alternateActive_) {
            // RGB pixels in the second genuine GPU region also prevent
            // discarding the completed SAME-Present Draw capture.
            D3D11_MAPPED_SUBRESOURCE beforeAlt{}, afterAlt{};
            const HRESULT a = ctx->Map(baselineAlternate_.Get(), 0,
                D3D11_MAP_READ, 0u, &beforeAlt);
            if (a != S_OK || !beforeAlt.pData ||
                beforeAlt.RowPitch < width * 4u) {
                if (a == S_OK) ctx->Unmap(baselineAlternate_.Get(), 0);
                alternateValid = false;
            } else {
                const HRESULT b = ctx->Map(stagingAlternate_.Get(), 0,
                    D3D11_MAP_READ, 0u, &afterAlt);
                if (b != S_OK || !afterAlt.pData ||
                    afterAlt.RowPitch < width * 4u) {
                    if (b == S_OK) ctx->Unmap(stagingAlternate_.Get(), 0);
                    alternateValid = false;
                } else {
                    alternateValid = native_raw_has_rgb_delta(
                        beforeAlt.pData, beforeAlt.RowPitch,
                        afterAlt.pData, afterAlt.RowPitch,
                        width, height, alternateChanged);
                    ctx->Unmap(stagingAlternate_.Get(), 0);
                }
                ctx->Unmap(baselineAlternate_.Get(), 0);
            }
        }
        ctx->Unmap(staging_.Get(), 0);
        ctx->Unmap(baseline_.Get(), 0);
        if (!valid || !alternateValid) {
            pending_ = false; quarantined_ = true;
            return;
        }
        if (changed || alternateChanged) {
            rgbEvidenceConfirmed_ = true; // preserve for the actual Present
            return;
        }
        if (captureEpoch_.retire_same_present_zero_rgb(
                presentSerial, pending_, true, false)) {
            pending_ = false;
            drawPair_.reset();
            ++zeroRgbRearmsThisPresent_;
            ++zeroRgbRetiredCopies_;
        }
    }
    NativeRawPreviewResult queue_before_draw(
        ID3D11Device* dev, ID3D11DeviceContext* ctx,
        ID3D11Texture2D* color) noexcept {
        if (!dev || !ctx || !color || pending_ || quarantined_)
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
        if (!stagingAlternate_ || !baselineAlternate_) {
            D3D11_TEXTURE2D_DESC dst{};
            staging_->GetDesc(&dst);
            if (!stagingAlternate_ && FAILED(dev->CreateTexture2D(
                    &dst, nullptr, stagingAlternate_.GetAddressOf())))
                return NativeRawPreviewResult::GpuFailure;
            if (!baselineAlternate_ && FAILED(dev->CreateTexture2D(
                    &dst, nullptr, baselineAlternate_.GetAddressOf())))
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
        NativeRawDualTile tiles{};
        if (!native_raw_dual_draw_tile(
                src.Width, src.Height, width, height, draw,
                static_cast<std::uint32_t>(capture_), tiles))
            return NativeRawPreviewResult::NoDraw;
        ++capture_;
        region_ = D3D11_BOX{tiles.first.x, tiles.first.y, 0u,
                            tiles.first.x + width, tiles.first.y + height, 1u};
        alternateActive_ = tiles.hasSecond;
        regionAlternate_ = alternateActive_
            ? D3D11_BOX{tiles.second.x, tiles.second.y, 0u,
                        tiles.second.x + width, tiles.second.y + height, 1u}
            : D3D11_BOX{};
        ctx->CopySubresourceRegion(baseline_.Get(), 0, 0, 0, 0,
                                   color, 0, &region_);
        if (alternateActive_)
            ctx->CopySubresourceRegion(baselineAlternate_.Get(), 0, 0, 0, 0,
                                       color, 0, &regionAlternate_);
        return NativeRawPreviewResult::CopyQueued;
    }
    Microsoft::WRL::ComPtr<ID3D11Texture2D> staging_, baseline_;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> stagingAlternate_, baselineAlternate_;
    D3D11_BOX region_{}, regionAlternate_{};
    bool alternateActive_ = false;
    NativeRawDrawPair drawPair_{};
    Microsoft::WRL::ComPtr<ID3D11Query> event_;
    Microsoft::WRL::ComPtr<IDirect3DSurface9> surface_, surfaceAlternate_;
    IDirect3DDevice9* gameOwner_ = nullptr;
    ID3D11Device* gpuOwner_ = nullptr;
    D3DFORMAT format_ = D3DFMT_UNKNOWN;
    std::uint64_t lastDraws_ = 0, capture_ = 0;
    bool pending_ = false;
    bool quarantined_ = false;
    std::uint64_t recoveredLateCopies_ = 0u;
    std::uint64_t zeroRgbRetiredCopies_ = 0u;
    std::uint64_t rearmSerial_ = (std::numeric_limits<std::uint64_t>::max)();
    std::uint32_t zeroRgbRearmsThisPresent_ = 0u;
    bool rgbEvidenceConfirmed_ = false;
    NativeRawGpuCaptureEpoch captureEpoch_{};
    NativeRawChangedPixelWindow changedWindow_{};
};
} // namespace outrun::vr::dx11
