#pragma once
#include <cstdint>

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
    // depth-only D32 native DSV may replay clipped D3D9 Z rectangles. Unlike
    // ClearDepthStencilView, D3D11.1 ClearView accepts bounded rectangles on
    // depth-only resources. Missing depth/owner/context must preserve DX9Ex.
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
} // namespace outrun::vr::dx11::live_game_frame
