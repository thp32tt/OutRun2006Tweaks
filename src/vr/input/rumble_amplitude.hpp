#pragma once

// VR-side adaptation of the pinned Wheel FFB v0.2 game's legacy XInput rumble.
// The released DirectInput wheel engine is immutable on this branch.
// Never cast an unchecked floating-point physics value to an integer: NaN,
// infinity, or a large magnitude would otherwise cause undefined behavior.
#include <cmath>
#include <cstdint>

namespace OutRunVR::Input
{
    inline std::uint16_t RumbleAmplitudeToWord(float amplitude) noexcept
    {
        if (!std::isfinite(amplitude) || amplitude <= 0.0f)
            return 0;
        if (amplitude >= 1.0f)
            return UINT16_MAX;
        return static_cast<std::uint16_t>(amplitude * 65535.0f);
    }
}
