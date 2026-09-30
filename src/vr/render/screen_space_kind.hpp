#pragma once

#include <cstdint>

namespace OutRunVR::Render
{
    enum class ScreenSpaceKind : std::uint8_t
    {
        None,
        Hud2D,
        FlatPerspectiveEffect
    };
}
