#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    void FailClosedStereoEligibility() noexcept;
    void ResetStereoBaselineTracking() noexcept;
    void FailClosedRasterReplayState(
        IDirect3DDevice9* device, const char* site) noexcept;
}
