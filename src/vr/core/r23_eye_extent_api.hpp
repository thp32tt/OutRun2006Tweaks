#pragma once
// Common R23 stereo owner includes both production-safe R26 and newer R29.
// Overlay borrows only validated eye dimensions, not transport ownership.
#include <cstdint>

namespace OutRunVRStereo
{
    // F11 needs one valid host publication, not two independently sampled eyes.
    bool R23TryGetPublishedEyeExtentPair(std::uint32_t out[4]) noexcept;
    bool R23TryGetPublishedEyeExtent(std::uint32_t eye,
        std::uint32_t& width, std::uint32_t& height) noexcept;
}
