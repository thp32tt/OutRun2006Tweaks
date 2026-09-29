#pragma once

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

namespace OutRunVR::DebugModes
{
    inline int HudCoordMode() noexcept
    {
        static const int mode = []() noexcept {
            char text[8]{};
            if (GetEnvironmentVariableA(
                    "OUTRUN_VR_HUD_COORD_MODE",
                    text, static_cast<DWORD>(sizeof(text))) == 0)
                return 0;
            if (text[0] < '0' || text[0] > '4')
                return 0;
            return static_cast<int>(text[0] - '0');
        }();
        return mode;
    }

    inline int HudProbeMode() noexcept
    {
        static const int mode = []() noexcept {
            char text[8]{};
            const DWORD len = GetEnvironmentVariableA(
                "OUTRUN_VR_HUD_PROBE", text,
                static_cast<DWORD>(sizeof(text)));
            if (len == 0 || len >= sizeof(text))
                return 0;
            int value = 0;
            for (DWORD i = 0; i < len; ++i)
            {
                if (text[i] < '0' || text[i] > '9')
                    return 0;
                value = value * 10 + int(text[i] - '0');
            }
            return (value >= 1 && value <= 20) ? value : 0;
        }();
        return mode;
    }

}
