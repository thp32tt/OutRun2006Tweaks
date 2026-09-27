#pragma once

namespace OutRunVR::SafetyPolicy
{
    struct StereoReplayState
    {
        bool gameDevice = false;
        bool internalStereoPass = false;
        bool targetBackBuffer = false;
        bool stereoWanted = false;
        bool stereoSeeded = false;
        bool runtimeEligible = false;
        bool recoveryPending = false;
        bool poseWarmup = false;
        bool frameStereoIncomplete = false;
        bool deferredDepth = false;
        bool depthMirrorable = false;
        bool auxRenderTargetActive = false;
        bool forceMonoShadow = false;
        bool occlusionTrackingUnavailable = false;
        bool activeOcclusionQuery = false;
    };

    constexpr bool CanReplayStereo(
        const StereoReplayState& s) noexcept
    {
        return s.gameDevice &&
            !s.internalStereoPass &&
            s.targetBackBuffer &&
            s.stereoWanted &&
            s.stereoSeeded &&
            s.runtimeEligible &&
            !s.recoveryPending &&
            !s.poseWarmup &&
            !s.frameStereoIncomplete &&
            !s.deferredDepth &&
            s.depthMirrorable &&
            !s.auxRenderTargetActive &&
            !s.forceMonoShadow &&
            !s.occlusionTrackingUnavailable &&
            !s.activeOcclusionQuery;
    }
}
