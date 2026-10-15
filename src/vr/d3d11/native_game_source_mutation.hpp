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
    [[nodiscard]] static constexpr bool invalidates_full_game_frame(
        bool fullMode, bool succeeded, bool gameOwner,
        bool destinationIsClearedBackbuffer, bool selfUpload) noexcept {
        return fullMode && succeeded && gameOwner &&
            destinationIsClearedBackbuffer && !selfUpload;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
