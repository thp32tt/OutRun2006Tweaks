#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    IDirect3DSurface9* TrackedDepthStencilSnapshot() noexcept;
    bool TrackedDepthStencilHasStencil() noexcept;
    bool LeftDrawMayWriteDepthLive(IDirect3DDevice9* device) noexcept;
    bool LeftDrawMayWriteStencilLive(IDirect3DDevice9* device) noexcept;
    void InvalidateRightDepthStencilForLeftWrite(
        IDirect3DDevice9* device) noexcept;
}
