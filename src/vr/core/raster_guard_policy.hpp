#pragma once

namespace OutRunVR::Core
{
    constexpr bool ShouldGuardStereoRaster(
        bool gameDevice,
        bool internalStereoPass,
        bool stateBlockRecording,
        bool stereoWanted,
        bool mainBackbuffer) noexcept
    {
        return gameDevice &&
            !internalStereoPass &&
            !stateBlockRecording &&
            stereoWanted &&
            mainBackbuffer;
    }

    static_assert(ShouldGuardStereoRaster(true, false, false, true, true));
    static_assert(!ShouldGuardStereoRaster(false, false, false, true, true));
    static_assert(!ShouldGuardStereoRaster(true, true, false, true, true));
    static_assert(!ShouldGuardStereoRaster(true, false, true, true, true));
    static_assert(!ShouldGuardStereoRaster(true, false, false, false, true));
    static_assert(!ShouldGuardStereoRaster(true, false, false, true, false));
}
