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
};
} // namespace OutRunVR::StereoLowerDraw
