#pragma once
#include <cstdint>

namespace OutRunVrNativeEyePair
{
    // Source routing is a property of the LAST successfully committed frame,
    // not the presence of cached shared handles or a prior stereo snapshot.
    enum class StereoSourceRoute : std::uint8_t { None, DirectGpu, Sbs };

    [[nodiscard]] constexpr StereoSourceRoute ChooseStereoSource(
        bool directCommitted, bool leftEyeReady, bool rightEyeReady,
        bool sbsCommitted, bool sbsViewReady) noexcept
    {
        if (directCommitted && leftEyeReady && rightEyeReady)
            return StereoSourceRoute::DirectGpu;
        if (sbsCommitted && sbsViewReady)
            return StereoSourceRoute::Sbs;
        return StereoSourceRoute::None;
    }
}
