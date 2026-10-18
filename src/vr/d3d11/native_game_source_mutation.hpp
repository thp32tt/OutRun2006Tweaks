#pragma once
#include <array>
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
// D3D9 can ColorFill several rectangles after its whole-backbuffer Clear but
// before the first Draw. Replay those game-authored fills IN ORDER after the
// native full-frame clear and before the first native Draw. Entries bind to
// the exact canonical backbuffer; overflow/foreign writes fail closed.
struct GameNativePreDrawFills {
    struct Fill {
        std::int64_t left{}, top{}, right{}, bottom{};
        std::uint32_t argb{};
    };
    static constexpr std::uint32_t kCapacity = 16u;
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
        if (!currentDevice || !currentBackbuffer ||
            (count && !belongs_to(currentDevice, currentBackbuffer)))
            return false;
        GameNativeSourceMutation::ColorFillRect clipped{};
        const auto coverage = GameNativeSourceMutation::classify_color_fill_rect(
            left, top, right, bottom, width, height, clipped);
        if (coverage == GameNativeSourceMutation::ColorFillClip::Invalid)
            return false;
        if (coverage == GameNativeSourceMutation::ColorFillClip::Empty)
            return true; // The original game wrote nothing; consume no tile slot.
        if (count >= kCapacity) return false;
        if (!count) {
            device = currentDevice;
            backbuffer = currentBackbuffer;
        }
        entries[count++] = {clipped.left, clipped.top, clipped.right,
                            clipped.bottom, color};
        return true;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
