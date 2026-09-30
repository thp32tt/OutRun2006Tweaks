#pragma once

#include <d3d9.h>
#include "../runtime_eligibility.hpp"

namespace OutRunVRStereo
{
    bool EffectIsFragileLive(
        IDirect3DDevice9* device, bool& fragile) noexcept;

    bool GetSavedViewport(
        IDirect3DDevice9* device, D3DVIEWPORT9& viewport) noexcept;

    bool SetWvpBatch(
        IDirect3DDevice9* device, const float* constants) noexcept;

    bool RestoreRightPassState(
        IDirect3DDevice9* device,
        IDirect3DSurface9* savedRt,
        IDirect3DSurface9* savedDepth,
        const D3DVIEWPORT9& savedViewport,
        const float* originalConstants,
        bool restoreWvp) noexcept;

    OutRunVR::RuntimeEligibility::InstallState
    ReviewInstallState() noexcept;
}
