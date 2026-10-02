#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    void FailClosedStereoEligibility() noexcept;
    // R22 remains the Reset owner; this declaration only makes the existing
    // hook destination link-visible to independently compiled upper overlays.
    HRESULT __stdcall ResetDestR22(IDirect3DDevice9* device,
        D3DPRESENT_PARAMETERS* params);
    void ResetStereoBaselineTracking() noexcept;
    void FailClosedRasterReplayState(
        IDirect3DDevice9* device, const char* site) noexcept;
}
