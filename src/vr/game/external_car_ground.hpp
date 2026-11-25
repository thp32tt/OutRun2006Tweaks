#pragma once
// Ferrari external OVC placement: conservative static floor guard.
// Pure/portable; used only to place the visual sidecar and NEVER alter
// original game simulation, collision, wheel physics or VR camera.
//
// Input modelMinY is the lowest indexed local-space vertex from a validated
// OVC. The caller must verify model ancestry, per-car native axis/scale and
// the exact player's existing car before calling this helper.
// This is not a terrain raycast and cannot prove dynamic suspension clearance.
#include <cmath>
#include <algorithm>

namespace OutRunVR::DinoSidecar {

// Shared contract: the world-space pose consumer must not silently discard
// an already accepted lift in (1.0, 1.25] metres.
constexpr float kMaximumExternalFloorLift=1.25f;
inline float SanitizeExternalFloorLift(float lift) noexcept {
    return std::isfinite(lift) && lift>=-0.25f &&
           lift<=kMaximumExternalFloorLift ? lift : 0.f;
}

inline bool ComputeExternalFloorLift(float requestedLift,
                                     float modelMinY,
                                     float& appliedLift) noexcept {
    // Car-space Y axis is up in the verified stock F50/F40/GTO OVC exporters.
    // Models far outside the already native-aligned vehicle envelope are
    // rejected rather than floating or sinking an untrusted asset.
    if (!std::isfinite(requestedLift) ||
        requestedLift < -0.25f || requestedLift > 1.0f ||
        !std::isfinite(modelMinY) ||
        modelMinY < -1.20f || modelMinY > 0.25f)
        return false;
    constexpr float kMinimumStaticClearance=0.035f; // 3.5 cm
    const float lift=(std::max)(requestedLift,
        kMinimumStaticClearance-modelMinY);
    if(!std::isfinite(lift) || lift>kMaximumExternalFloorLift)
        return false;
    appliedLift=lift;
    return true;
}
} // namespace OutRunVR::DinoSidecar
