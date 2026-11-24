#pragma once
#include "../d3d9/r30_state_restore_result.hpp"

namespace OutRunVR::StereoLowerDraw {
// Distinguish a safe pre-raster decline from an actual GPU HRESULT.
// E_NOTIMPL is a valid failure HRESULT; it cannot also mean "not drawn".
template<class Result>
struct Attempt final {
    bool handled=false;
    Result hr{};
    static constexpr Attempt Declined() noexcept { return {}; }
    static constexpr Attempt Handled(Result hr) noexcept { return {true,hr}; }
    static constexpr Attempt AfterDraw(
        Result hr, bool restored, Result restoreError) noexcept {
        return Handled(R30StateRestore::ResultAfterRestore(
            hr,restored,restoreError));
    }
    // Decline only if no native draw was attempted and restoration was clean.
    // Preserve real driver HRESULTs even when they equal the decline sentinel.
    static constexpr Attempt AfterRoute(Result hr, bool attempted, bool restored,
                                        Result declineHr, Result restoreError) noexcept {
        if (!attempted && restored && hr == declineHr) return Declined();
        if (!attempted && !restored && hr == declineHr) return Handled(restoreError);
        return AfterDraw(hr, restored, restoreError);
    }
};
} // namespace OutRunVR::StereoLowerDraw
