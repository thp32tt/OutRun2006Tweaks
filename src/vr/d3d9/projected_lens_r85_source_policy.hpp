#pragma once
#include <cstdint>

// Quest 2026-11-01 source/Pose trace: exact C993 PMT 0x570006 is the
// INNER optical flare, not the sun disc. It recorded cameraSynced=1
// but remained HMD-locked when that value bypassed the common head
// inverse. Restrict this correction to that exact original object:
// 0x570002 (sun), 0x57000F and 0x570010 keep their established route.
// Outer optical discs continue using their prior head-inverse route.
namespace OutRunVR::LensCentre
{
    constexpr bool R85InnerOpticalFlareNeedsHeadInverse(
        std::uint32_t objectId) noexcept
    {
        return objectId == 0x570006u;
    }

    constexpr bool R85UseRecordedCameraSync(
        std::uint32_t objectId, bool existingOuterOpticalFlare,
        bool recordedCameraSynced) noexcept
    {
        return recordedCameraSynced &&
            !existingOuterOpticalFlare &&
            !R85InnerOpticalFlareNeedsHeadInverse(objectId);
    }

    static_assert(!R85UseRecordedCameraSync(0x570006u, false, true));
    static_assert(R85UseRecordedCameraSync(0x570002u, false, true));
    static_assert(R85UseRecordedCameraSync(0x57000Fu, false, true));
    static_assert(R85UseRecordedCameraSync(0x570010u, false, true));
    static_assert(!R85UseRecordedCameraSync(0x570003u, true, true));
    static_assert(!R85UseRecordedCameraSync(0x570006u, false, false));
}
