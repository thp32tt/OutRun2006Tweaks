#pragma once
// Explicit R31 support/state-owner boundary consumed by R32.
//
// This seam is behavior-neutral: R31 keeps StateBlock/cache/telemetry ownership
// and R32 keeps the same review/reset/transport policy. It only removes R32's
// dependence on R31 anonymous/private helper names so the textual R31 include
// can be retired in a later bounded translation-unit split.

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <cstdint>
#include <d3d9.h>
#include "../runtime_eligibility.hpp"

#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

namespace OutRunVRRenderer
{
    struct LatchedStereoFrame;
}

namespace OutRunVRStereo
{
    struct R31SupportFrameSnapshot
    {
        std::uint64_t main = 0;
        std::uint64_t offscreen = 0;
        std::uint64_t aux = 0;
        std::uint64_t fastWorld = 0;
        std::uint64_t hud = 0;
        std::uint64_t fallback = 0;
        std::uint64_t fragile = 0;
        std::uint64_t unstable = 0;
    };

    struct R31SupportFastWorldConstants
    {
        float originalConstants[16]{};
        float eyeConstants[2][16]{};
        std::uint32_t poseSequence = 0;
    };

    R31SupportFrameSnapshot R31SupportTelemetryFrameSnapshot() noexcept;
    std::uint64_t R31SupportTelemetryLiveWvpChecks() noexcept;
    std::uint64_t R31SupportTelemetryLiveWvpRejects() noexcept;
    void R31SupportResetFastPathState() noexcept;
    bool R31SupportGetSavedViewport(
        IDirect3DDevice9* device, D3DVIEWPORT9& viewport) noexcept;
    void R31SupportObserveDraw(IDirect3DDevice9* device) noexcept;
    void R31SupportDiscardUnreliableDrawCaches() noexcept;
    void R31SupportNoteFallback() noexcept;
    void R31SupportNoteFastWorld() noexcept;
    void R31SupportNoteFragile() noexcept;
    void R31SupportNoteHud() noexcept;
    void R31SupportNoteUnstable() noexcept;
    bool R31SupportBuildFastWorldConstants(
        IDirect3DDevice9* device,
        const OutRunVRRenderer::LatchedStereoFrame& stereo,
        R31SupportFastWorldConstants& out) noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R31SupportInstallStatus() noexcept;
}
