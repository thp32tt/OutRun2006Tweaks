#pragma once

#include "d3d9_raster_state.hpp"

namespace OutRunVRStereo
{
    OutRunVR::State::D3D9RasterSnapshot GetTrackedRasterShadow() noexcept;
    void SetTrackedRasterShadow(
        const OutRunVR::State::D3D9RasterSnapshot& snapshot) noexcept;
    void InvalidateTrackedRasterShadow() noexcept;
    bool IsTrackedStateBlockReliable() noexcept;
}
