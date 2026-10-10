#pragma once
// R29 functional-owner ABI consumed by the independently compiled R30 TU.
// Preserve the original R29 classification, install epoch, stereo recovery,
// and two-eye accounting. This API does not install or relocate physical hooks.
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <cstdint>
#include <d3d9.h>
#include "../runtime_eligibility.hpp"

namespace OutRunVRStereo
{
    bool R29OwnerStableStereoBase(IDirect3DDevice9* device) noexcept;
    bool R29OwnerFragileEffectCached(
        IDirect3DDevice9* device, bool& fragile) noexcept;
    void R29OwnerArmMonoSafety(std::uint64_t extraPresents = 2) noexcept;
    void R29OwnerNoteStableTwoEyeDraw() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R29OwnerInstallStatus() noexcept;
    // Snapshot of the *existing* R29/lower draw and resource state. Borrowed
    // surfaces must not be released or retained by the consumer. This is a
    // value-only transfer; the R29 TU remains sole owner of those resources.
    struct R29OwnerFrameSnapshot
    {
        UINT width = 0;
        UINT height = 0;
        IDirect3DSurface9* backBuffer = nullptr;
        IDirect3DSurface9* rightEyeSurface = nullptr;
        IDirect3DSurface9* rightEyeDepth = nullptr;
        IDirect3DSurface9* trackedDepthStencil = nullptr;
        std::uint64_t presentEpoch = 0;
        std::uint32_t poseSequence = 0;
        bool hadWorldStereo = false;
        bool hadDuplicatedDraw = false;
        bool rightDrawFailed = false;
        bool stereoIncomplete = false;
        bool rightDepthSynchronized = false;
        bool rightStencilSynchronized = false;
    };
    R29OwnerFrameSnapshot R29OwnerCaptureFrameSnapshot() noexcept;
    // Only R29 accesses lower-chain IPC and adapter lifetime state.
    // Consumers receive copied dimensions/identity, never the shared pointer.
    bool R29OwnerRecommendedEyeExtent(std::uint32_t eye,
        std::uint32_t& width, std::uint32_t& height) noexcept;
    struct R29OwnerTransportIdentity
    {
        std::uint32_t hostPid = 0;
        std::uint32_t hostAdapterLuidLow = 0;
        std::uint32_t hostAdapterLuidHigh = 0;
    };
    bool R29OwnerTryGetDirectTransportIdentity(
        R29OwnerTransportIdentity& out) noexcept;
    bool R29OwnerStereoWanted() noexcept;
    bool R29OwnerTargetIsBackBuffer() noexcept;
    bool R29OwnerExchangeInternalStereoPass(bool active) noexcept;
}
