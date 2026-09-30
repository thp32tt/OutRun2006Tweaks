#pragma once

#include <Windows.h>
#include "../stereo_failure.hpp"

namespace OutRunVRStereo
{
    void NoteStereoLeftDraw() noexcept;
    bool IsStereoSeeded() noexcept;

    void ReportStereoFailure(
        OutRunVR::StereoFailureReason reason,
        const char* site, HRESULT hr = E_FAIL) noexcept;
}
