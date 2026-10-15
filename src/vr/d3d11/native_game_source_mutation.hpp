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
    [[nodiscard]] static constexpr bool invalidates_full_game_frame(
        bool fullMode, bool succeeded, bool gameOwner,
        bool destinationIsClearedBackbuffer, bool selfUpload) noexcept {
        return fullMode && succeeded && gameOwner &&
            destinationIsClearedBackbuffer && !selfUpload;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
