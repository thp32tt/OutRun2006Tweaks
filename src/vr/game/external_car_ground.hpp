#pragma once
// Ferrari external OVC placement: conservative static floor guard.
// Pure/portable; used only to place the visual sidecar and NEVER alter
// original game simulation, collision, wheel physics or VR camera.
//
// Input modelMinY is the actual lowest local-space vertex from a validated
// OVC. The caller must verify model ancestry, per-car native axis/scale and
// the exact player's existing car before calling this helper.
// This is not a terrain raycast and cannot prove dynamic suspension clearance.
#include <cmath>
#include <algorithm>

namespace OutRunVR::DinoSidecar {

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
    constexpr float kMaximumLift=1.25f;
    const float lift=std::max(requestedLift,
        kMinimumStaticClearance-modelMinY);
    if(!std::isfinite(lift) || lift>kMaximumLift)
        return false;
    appliedLift=lift;
    return true;
}
} // namespace OutRunVR::DinoSidecar
