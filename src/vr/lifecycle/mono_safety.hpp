#pragma once

#include <cstdint>

namespace OutRunVRStereo
{
    void ArmMonoSafety(std::uint64_t extraPresents = 2) noexcept;
    bool IsForcedMonoShadow() noexcept;
    void NoteDrawTimeZeroDisparity() noexcept;
}
