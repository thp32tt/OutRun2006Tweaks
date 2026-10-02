#pragma once

#include <d3d9.h>
#include <cstdint>
#include <type_traits>
#include "../runtime_eligibility.hpp"

namespace OutRunVRRenderer { struct LatchedStereoFrame; }

namespace OutRunVRStereo
{
    using FailClosedDrawCallback = HRESULT(*)(void*) noexcept;
    HRESULT RunLowerFailClosed(IDirect3DDevice9* device,
        FailClosedDrawCallback callback, void* context) noexcept;

    template <typename LowerDraw>
    HRESULT LowerFailClosed(IDirect3DDevice9* device, LowerDraw&& lowerDraw) noexcept
    {
        using DrawType = std::remove_reference_t<LowerDraw>;
        auto callback = [](void* context) noexcept -> HRESULT {
            return (*static_cast<DrawType*>(context))();
        };
        return RunLowerFailClosed(device, callback, &lowerDraw);
    }

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
