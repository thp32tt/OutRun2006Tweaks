#pragma once
#include <array>
#include <cstdint>
#include "native_game_pre_draw_tile_coalesce.hpp"

namespace outrun::vr::dx11::live_game_frame {
// The original D3D9 game may write directly into its canonical backbuffer
// between Draw and Present without issuing another Draw/Clear. The diagnostic
// D3D11 scene cannot represent UpdateSurface, StretchRect or ColorFill yet.
// Preserve game output by invalidating that entire native source batch.
// Other render targets, failed operations and native's own same-Present
// upload must never interrupt the game or force needless batch retirement.
struct GameNativeSourceMutation {
    // Direct backbuffer CPU LockRect/GetDC writes have no matching D3D11
    // draw command. Read-only locks, failures and staging SYSTEMMEM locks
    // cannot modify the owned game frame. The observer additionally verifies
    // the exact canonical backbuffer/device identity before aborting.
    [[nodiscard]] static constexpr bool cpu_surface_write_possible(
        bool succeeded, bool readOnly, bool defaultPool) noexcept {
        return succeeded && !readOnly && defaultPool;
    }
    // Mirror a successful *whole* main D3D9 ColorFill on the native RTV;
    // unproved, partial, foreign or failed operations keep D3D9 fallback.
    [[nodiscard]] static constexpr bool mirrors_full_color_fill(
        bool fullMode, bool succeeded, bool gameOwner,
        bool canonicalBackbuffer, bool wholeSurface,
        bool activeOrPreDraw, bool nativeTargetReady) noexcept {
        return fullMode && succeeded && gameOwner && canonicalBackbuffer &&
               wholeSurface && activeOrPreDraw && nativeTargetReady;
    }
    // The real D3D9 ColorFill succeeded before native replay is attempted.
    // A driver can clip that RECT against its destination surface: replay
    // only the actual overlapping pixels. Entirely outside valid rectangles
    // write no pixels and must not break a complete menu/car/race native batch.
    // Invalid extents or sizes not representable by D3D11_RECT fail closed.
    enum class ColorFillClip : std::uint8_t { Invalid, Empty, Pixels };
    struct ColorFillRect { std::int64_t left{}, top{}, right{}, bottom{}; };
    [[nodiscard]] static constexpr ColorFillClip classify_color_fill_rect(
        std::int64_t l, std::int64_t t, std::int64_t r, std::int64_t b,
        std::uint32_t width, std::uint32_t height,
        ColorFillRect& out) noexcept {
        out = {};
        if (!width || !height || width > 0x7fffffffu ||
            height > 0x7fffffffu || r <= l || b <= t)
            return ColorFillClip::Invalid;
        const auto w = static_cast<std::int64_t>(width);
        const auto h = static_cast<std::int64_t>(height);
        out = { l > 0 ? l : 0, t > 0 ? t : 0,
                r < w ? r : w, b < h ? b : h };
        return out.left < out.right && out.top < out.bottom
            ? ColorFillClip::Pixels : ColorFillClip::Empty;
    }
    // A bounded partial ColorFill can be replayed through D3D11.1 ClearView
    // only *after* native Draw has seeded a complete frame. Unknown/outside
    // extents must fail closed rather than clearing unrelated native pixels.
    [[nodiscard]] static constexpr bool bounded_color_fill_rect(
        std::int64_t left, std::int64_t top,
        std::int64_t right, std::int64_t bottom,
        std::uint32_t width, std::uint32_t height) noexcept {
        return width != 0u && height != 0u &&
            left >= 0 && top >= 0 && right > left && bottom > top &&
            right <= static_cast<std::int64_t>(width) &&
            bottom <= static_cast<std::int64_t>(height);
    }
    [[nodiscard]] static constexpr bool mirrors_partial_color_fill(
        bool fullMode, bool succeeded, bool sameBackbuffer,
        bool activeNativeBatch, bool targetReady, bool boundedRect) noexcept {
        return fullMode && succeeded && sameBackbuffer && activeNativeBatch &&
               targetReady && boundedRect;
    }

    // Only a live full-frame Draw with matching canonical Z and an allocated
    // depth-only D32 native DSV may replay clipped source-game Z rectangles.
    // D3D11.1 ClearView or the owned D3D11.0 GPU raster updates exact pixels.
    // Missing depth/owner/context always preserves DX9Ex.
    [[nodiscard]] static constexpr bool mirrors_partial_depth_clear(
        bool full, bool sameMainDepth, bool activeBatch,
        bool nativeDepthReady, bool d32DepthView, bool context1Ready) noexcept {
        return full && sameMainDepth && activeBatch && nativeDepthReady &&
               d32DepthView && context1Ready;
    }
    // Exact D3D9 TARGET and optional simultaneous Z region replay in an
    // already live DX11 menu/car/race Draw batch.
    // menu/car/race Draw batch. D3D11.1 ClearView updates only clipped pixels.
    static constexpr std::uint32_t kMaxPartialTargetClearRects = 32u;
    struct TargetClearRect { std::int64_t left{}, top{}, right{}, bottom{}; };
    [[nodiscard]] static constexpr bool mirrors_partial_target_clear(
        bool full, bool targetOnly, bool sameOwner, bool sameBackbuffer,
        bool activeBatch, bool targetReady, bool noMrt) noexcept {
        return full && targetOnly && sameOwner && sameBackbuffer &&
               activeBatch && targetReady && noMrt;
    }
    // D3D9 Clear rectangles are screen-space, intersected with the current
    // viewport. A valid rectangle fully outside it writes no pixels: this is
    // NOT a failed native replay, and a mixed batch can still be preserved.
    // Malformed rectangles and unknown viewport extents remain fail-closed.
    enum class TargetClearClip : std::uint8_t { Invalid, Empty, Pixels };
    [[nodiscard]] static constexpr TargetClearClip classify_target_clear_rect(
        std::int64_t l, std::int64_t t, std::int64_t r, std::int64_t b,
        std::uint32_t vx, std::uint32_t vy,
        std::uint32_t vw, std::uint32_t vh,
        std::uint32_t width, std::uint32_t height,
        TargetClearRect& out) noexcept {
        out = {};
        if (!vw || !vh || !width || !height ||
            vx >= width || vy >= height || r <= l || b <= t ||
            static_cast<std::uint64_t>(vx) + vw > width ||
            static_cast<std::uint64_t>(vy) + vh > height)
            return TargetClearClip::Invalid;
        const auto x0 = static_cast<std::int64_t>(vx);
        const auto y0 = static_cast<std::int64_t>(vy);
        out = { l > x0 ? l : x0, t > y0 ? t : y0,
                r < x0 + vw ? r : x0 + vw,
                b < y0 + vh ? b : y0 + vh };
        return out.left < out.right && out.top < out.bottom
            ? TargetClearClip::Pixels : TargetClearClip::Empty;
    }
    [[nodiscard]] static constexpr bool clipped_target_clear_rect(
        std::int64_t l, std::int64_t t, std::int64_t r, std::int64_t b,
        std::uint32_t vx, std::uint32_t vy,
        std::uint32_t vw, std::uint32_t vh,
        std::uint32_t width, std::uint32_t height,
        TargetClearRect& out) noexcept {
        return classify_target_clear_rect(
            l, t, r, b, vx, vy, vw, vh, width, height, out)
            == TargetClearClip::Pixels;
    }
    [[nodiscard]] static constexpr bool invalidates_full_game_frame(
        bool fullMode, bool succeeded, bool gameOwner,
        bool destinationIsClearedBackbuffer, bool selfUpload) noexcept {
        return fullMode && succeeded && gameOwner &&
            destinationIsClearedBackbuffer && !selfUpload;
    }
};
// D3D9 can ColorFill several rectangles after its whole-backbuffer Clear but
// before the first Draw. Replay those game-authored fills IN ORDER after the
// native full-frame clear and before the first native Draw. Entries bind to
// the exact canonical backbuffer. ColorFill is an unconditional pixel overwrite:
// a newer rect can retire wholly covered older writes without changing the
// final ordered game pixels. Unrelated overflow/foreign writes fail closed.
struct GameNativePreDrawFills {
    struct Fill {
        std::int64_t left{}, top{}, right{}, bottom{};
        std::uint32_t argb{};
    };
    static constexpr std::uint32_t kCapacity = 16u;
    // D3D9 source Clear rectangles may clip or overwrite into fewer replay
    // tiles. Bound source processing separately from the 16 stored GPU tiles.
    static constexpr std::uint32_t kMaxPreDrawTargetClearSourceRects = 128u;
    std::array<Fill, kCapacity> entries{};
    std::uintptr_t device{}, backbuffer{};
    std::uint32_t count{};
    constexpr void discard() noexcept {
        device = backbuffer = 0u;
        count = 0u;
    }
    [[nodiscard]] constexpr bool belongs_to(
        std::uintptr_t currentDevice, std::uintptr_t currentBackbuffer) const noexcept {
        return count != 0u && device != 0u && backbuffer != 0u &&
            currentDevice == device && currentBackbuffer == backbuffer;
    }
    // A recorded ColorFill is replayable only on the exact source surface.
    // Recheck after a resize/reset and before submitting any native pixels.
    [[nodiscard]] constexpr bool replay_ready(
        std::uintptr_t currentDevice, std::uintptr_t currentBackbuffer,
        std::uint32_t width, std::uint32_t height) const noexcept {
        if (count == 0u) return true;
        if (!belongs_to(currentDevice, currentBackbuffer) ||
            count > kCapacity || width == 0u || height == 0u ||
            width > 0x7fffffffu || height > 0x7fffffffu)
            return false;
        for (std::uint32_t i = 0u; i < count; ++i) {
            const auto& fill = entries[i];
            if (fill.left < 0 || fill.top < 0 ||
                fill.right <= fill.left || fill.bottom <= fill.top ||
                fill.right > static_cast<std::int64_t>(width) ||
                fill.bottom > static_cast<std::int64_t>(height))
                return false;
        }
        return true;
    }
    [[nodiscard]] constexpr bool record(
        std::uintptr_t currentDevice, std::uintptr_t currentBackbuffer,
        std::int64_t left, std::int64_t top,
        std::int64_t right, std::int64_t bottom,
        std::uint32_t width, std::uint32_t height,
        std::uint32_t color) noexcept {
        if (!currentDevice || !currentBackbuffer || count > kCapacity ||
            (count && !belongs_to(currentDevice, currentBackbuffer)))
            return false;
        GameNativeSourceMutation::ColorFillRect clipped{};
        const auto coverage = GameNativeSourceMutation::classify_color_fill_rect(
            left, top, right, bottom, width, height, clipped);
        if (coverage == GameNativeSourceMutation::ColorFillClip::Invalid)
            return false;
        if (coverage == GameNativeSourceMutation::ColorFillClip::Empty)
            return true; // The original game wrote nothing; consume no tile slot.
        const Fill next{clipped.left, clipped.top, clipped.right,
                        clipped.bottom, color};
        const auto covers = [](const Fill& outer, const Fill& inner) constexpr {
            return outer.left <= inner.left && outer.top <= inner.top &&
                   outer.right >= inner.right && outer.bottom >= inner.bottom;
        };
        // Only the immediately preceding same-color write may subsume the
        // new write: an intervening differently colored fill could require it.
        if (count && entries[count - 1u].argb == color &&
            covers(entries[count - 1u], next))
            return true;
        // The latest opaque D3D9 ColorFill wins over every *fully* enclosed
        // earlier tile, regardless of intervening writes or earlier colors.
        // Determine capacity before mutating the recorded source transaction.
        // The game's 128-rectangle Clear may consist of many adjacent
        // strips. Compact ONLY an exact same-ARGB rectangular union while
        // preserving every surviving earlier overwrite in source order.
        // Stage the entire ledger so capacity failure cannot lose a pixel.
        auto staged = *this;
        std::uint32_t output = 0u;
        for (std::uint32_t i = 0u; i < count; ++i) {
            const Fill saved = entries[i];
            if (!covers(next, saved)) staged.entries[output++] = saved;
        }
        if (output && staged.entries[output - 1u].argb == color &&
            game_native_merge_ordered_overwrite(
                staged.entries[output - 1u], next)) {
            staged.count = output;
        } else {
            if (output >= kCapacity) return false;
            staged.entries[output++] = next;
            staged.count = output;
        }
        // A row of contiguous same-ARGB strips may later become an
        // identical-width adjacent row. Fold the last two surviving GPU
        // tiles recursively; only adjacent source-order overwrites can fuse.
        while (staged.count >= 2u &&
               staged.entries[staged.count - 2u].argb ==
                   staged.entries[staged.count - 1u].argb &&
               game_native_merge_ordered_overwrite(
                   staged.entries[staged.count - 2u],
                   staged.entries[staged.count - 1u]))
            --staged.count;
        if (!count) {
            staged.device = currentDevice;
            staged.backbuffer = currentBackbuffer;
        }
        *this = staged;
        return true;
    }

    // Successful game TARGET-only Clear before the first Draw is an ordered
    // backbuffer color overwrite, just like ColorFill. Stage the *entire*
    // D3DRECT batch to avoid publishing a prefix on capacity/owner failure.
    // The caller handles whole-surface Clears as a new scene epoch instead.
    template<class Rect>
    [[nodiscard]] constexpr bool record_target_clear(
        std::uintptr_t currentDevice, std::uintptr_t currentBackbuffer,
        std::uint32_t width, std::uint32_t height,
        std::uint32_t viewportX, std::uint32_t viewportY,
        std::uint32_t viewportWidth, std::uint32_t viewportHeight,
        std::uint32_t rectCount, const Rect* rects,
        std::uint32_t color) noexcept {
        if (!currentDevice || !currentBackbuffer ||
            rectCount > kMaxPreDrawTargetClearSourceRects ||
            (rectCount && !rects) ||
            (count && !belongs_to(currentDevice, currentBackbuffer)))
            return false;
        // D3DRECT uses signed LONG. Cast before the conditional operator:
        // otherwise the UINT viewport arm converts negative source coordinates
        // to UINT_MAX and rejects valid clipped game Clears.
        GameNativePreDrawFills staged = *this;
        for (std::uint32_t i = 0u; i < (rectCount ? rectCount : 1u); ++i) {
            const std::int64_t l = rectCount ? static_cast<std::int64_t>(rects[i].x1) : viewportX;
            const std::int64_t t = rectCount ? static_cast<std::int64_t>(rects[i].y1) : viewportY;
            const std::int64_t r = rectCount ? static_cast<std::int64_t>(rects[i].x2) :
                static_cast<std::int64_t>(viewportX) + viewportWidth;
            const std::int64_t b = rectCount ? static_cast<std::int64_t>(rects[i].y2) :
                static_cast<std::int64_t>(viewportY) + viewportHeight;
            GameNativeSourceMutation::TargetClearRect clipped{};
            const auto coverage = GameNativeSourceMutation::classify_target_clear_rect(
                l, t, r, b, viewportX, viewportY, viewportWidth,
                viewportHeight, width, height, clipped);
            if (coverage == GameNativeSourceMutation::TargetClearClip::Invalid)
                return false;
            if (coverage == GameNativeSourceMutation::TargetClearClip::Empty)
                continue; // D3D9 performed no pixel write.
            if (!staged.record(currentDevice, currentBackbuffer,
                               clipped.left, clipped.top,
                               clipped.right, clipped.bottom,
                               width, height, color))
                return false;
        }
        *this = staged;
        return true;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
