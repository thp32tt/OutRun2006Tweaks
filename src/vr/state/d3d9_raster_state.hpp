#pragma once

#include <Windows.h>
#include <d3d9.h>

namespace OutRunVR::State
{
    struct D3D9RasterSnapshot
    {
        RECT rect{};
        DWORD enabled = FALSE;
        D3DVIEWPORT9 viewport{};
        bool viewportValid = false;
        bool rectValid = false;
        bool enableValid = false;

        bool Valid() const noexcept
        {
            return viewportValid && rectValid && enableValid;
        }
    };
}
