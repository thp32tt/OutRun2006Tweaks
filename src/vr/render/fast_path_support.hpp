#pragma once

#include <d3d9.h>
#include <cstdint>
#include "../runtime_eligibility.hpp"

namespace OutRunVRRenderer { struct LatchedStereoFrame; }

namespace OutRunVRStereo
{
    struct FastWorldDispatchConstants
    {
        float originalConstants[16]{};
        float eyeConstants[2][16]{};
        std::uint32_t poseSequence = 0;
    };

    bool BuildFastWorldDispatchConstants(
        IDirect3DDevice9* device,
        const OutRunVRRenderer::LatchedStereoFrame& stereo,
        FastWorldDispatchConstants& out) noexcept;

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
