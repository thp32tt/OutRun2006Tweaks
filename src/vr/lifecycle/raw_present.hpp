#pragma once

#include <Windows.h>
#include <d3d9.h>

namespace OutRunVRStereo
{
    HRESULT CallRawPresent(
        IDirect3DDevice9* device,
        const RECT* sourceRect, const RECT* destRect,
        HWND destWindowOverride, const RGNDATA* dirtyRegion);
}
