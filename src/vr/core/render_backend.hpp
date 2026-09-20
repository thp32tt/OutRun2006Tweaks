#pragma once

#include <cstdint>

namespace OutRunVR
{
    // Shared renderer identifier for future backend selection.
    // This header intentionally contains no policy or backend-specific code.
    enum class RenderBackend : std::uint8_t
    {
        Auto = 0,
        D3D9TwoPass = 1,
        Dxvk = 2,
        Dx12 = 3,
    };
}
