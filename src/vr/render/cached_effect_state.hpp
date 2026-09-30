#pragma once

#include <Windows.h>
#include <cstdint>

namespace OutRunVR::Render
{
    struct CachedEffectState
    {
        DWORD alphaBlend = FALSE;
        DWORD alphaTest = FALSE;
        DWORD zWrite = TRUE;
        bool valid = false;
        std::uint64_t presentEpoch = 0;
        std::uint64_t drawSerial = 0;
    };
}

namespace OutRunVRStereo
{
    OutRunVR::Render::CachedEffectState CachedEffectStateSnapshot() noexcept;
    void ResetCachedEffectState() noexcept;
    void SetMonoSafetyThroughEpoch(std::uint64_t epoch) noexcept;
}
