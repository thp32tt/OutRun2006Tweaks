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
    [[nodiscard]] static constexpr bool invalidates_full_game_frame(
        bool fullMode, bool succeeded, bool gameOwner,
        bool destinationIsClearedBackbuffer, bool selfUpload) noexcept {
        return fullMode && succeeded && gameOwner &&
            destinationIsClearedBackbuffer && !selfUpload;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
