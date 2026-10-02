#pragma once

#include <Windows.h>
#include "../ipc/protocol.hpp"

namespace OutRunVRStereo
{
    void NoteStereoLeftDraw() noexcept;
    void UndoStereoLeftDraw() noexcept;
    bool IsStereoSeeded() noexcept;

    void ReportStereoFailure(
        OutRunVR::StereoFailureReason reason,
        const char* site, HRESULT hr = E_FAIL) noexcept;
    void ObserveLegacyStereoFailure(
        OutRunVR::StereoFailureReason before,
        const char* site, HRESULT hr) noexcept;
}
