#pragma once

#include <cstdint>

// Explicit VR render-pass policy shared by the D3D9 stereo and renderer-pose
// hardening layers.  The idea mirrors the compatibility/pass classification
// used by mature emulator VR implementations: classify first, then choose the
// least invasive rendering action.  This file intentionally contains no D3D9
// state access so the policy remains deterministic and compile-time testable.
namespace OutRunVR::PassPolicy
{
    enum class PoseInjectionPolicy : std::uint8_t
    {
        InternalStereo,
        MainBackbuffer,
        AuxiliaryStock
    };

    constexpr PoseInjectionPolicy ClassifyPoseInjection(
        bool internalStereo,
        bool mainBackbuffer,
        bool auxiliaryRenderTargetActive) noexcept
    {
        if (internalStereo)
            return PoseInjectionPolicy::InternalStereo;
        if (mainBackbuffer && !auxiliaryRenderTargetActive)
            return PoseInjectionPolicy::MainBackbuffer;
        return PoseInjectionPolicy::AuxiliaryStock;
    }

    constexpr bool AllowsPoseInjection(PoseInjectionPolicy policy) noexcept
    {
        return policy == PoseInjectionPolicy::MainBackbuffer;
    }

    enum class DrawReplayPolicy : std::uint8_t
    {
        Legacy,
        ForcedMonoShadow,
        UnsafeSingleExecution
    };

    constexpr DrawReplayPolicy ClassifyDrawReplay(
        bool gameDevice,
        bool internalStereo,
        bool mainBackbuffer,
        bool forceMonoShadow,
        bool stereoWanted,
        bool stereoSeeded,
        bool unsafeMrt,
        bool unsafeOcclusion) noexcept
    {
        if (!gameDevice || internalStereo || !mainBackbuffer)
            return DrawReplayPolicy::Legacy;
        if (forceMonoShadow)
            return DrawReplayPolicy::ForcedMonoShadow;
        if (stereoWanted && stereoSeeded && (unsafeMrt || unsafeOcclusion))
            return DrawReplayPolicy::UnsafeSingleExecution;
        return DrawReplayPolicy::Legacy;
    }

    // Compile-time policy invariants. These deliberately encode the safety
    // contract rather than individual hook implementation details.
    static_assert(ClassifyPoseInjection(false, true, false) ==
        PoseInjectionPolicy::MainBackbuffer);
    static_assert(ClassifyPoseInjection(false, true, true) ==
        PoseInjectionPolicy::AuxiliaryStock);
    static_assert(ClassifyPoseInjection(true, true, false) ==
        PoseInjectionPolicy::InternalStereo);

    static_assert(ClassifyDrawReplay(true, false, true, false, true, true, true, false) ==
        DrawReplayPolicy::UnsafeSingleExecution);
    static_assert(ClassifyDrawReplay(true, false, true, true, true, true, false, false) ==
        DrawReplayPolicy::ForcedMonoShadow);
    static_assert(ClassifyDrawReplay(true, false, false, false, true, true, true, true) ==
        DrawReplayPolicy::Legacy);
}
