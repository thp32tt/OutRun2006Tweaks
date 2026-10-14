#pragma once

#include <cstdint>

namespace OutRunVR::R30EarlyRhwShadow
{
    // The mask/value come from the D3D9 FVF contract. A declaration-backed
    // vertex buffer (FVF=0) has no creation-time proof and stays lazy.
    constexpr bool ExplicitXyzrhwFvf(std::uint32_t fvf,
        std::uint32_t positionMask, std::uint32_t xyZrhw) noexcept
    {
        return fvf != 0u && (fvf & positionMask) == xyZrhw;
    }

    // Never inspect a failed/unowned Lock or an external overlay. An exact
    // early-registered VB may be observed before the global draw-time arm;
    // an unknown VB must wait for the existing lazy stereo capture path.
    constexpr bool ObserveVertexLock(bool fullCapture,
        bool exactEarlyRegistration, bool externalOverlay,
        bool lockSucceeded, bool nonNullData) noexcept
    {
        return !externalOverlay && lockSucceeded && nonNullData &&
            (fullCapture || exactEarlyRegistration);
    }
}
