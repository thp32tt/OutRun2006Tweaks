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

    inline bool SameRasterSnapshot(
        const D3D9RasterSnapshot& a,
        const D3D9RasterSnapshot& b) noexcept
    {
        if (!a.Valid() || !b.Valid())
            return false;
        return a.viewport.X == b.viewport.X &&
            a.viewport.Y == b.viewport.Y &&
            a.viewport.Width == b.viewport.Width &&
            a.viewport.Height == b.viewport.Height &&
            a.viewport.MinZ == b.viewport.MinZ &&
            a.viewport.MaxZ == b.viewport.MaxZ &&
            a.rect.left == b.rect.left &&
            a.rect.top == b.rect.top &&
            a.rect.right == b.rect.right &&
            a.rect.bottom == b.rect.bottom &&
            a.enabled == b.enabled;
    }
}
