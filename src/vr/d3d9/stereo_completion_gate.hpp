#pragma once

// A left-eye HRESULT is the game's original draw result, not evidence that
// the stereo frame was actually completed. No successful-frame latch, pose
// metadata or VR HUD/world success telemetry may be published until BOTH
// GPU eyes and all state restoration have succeeded.
namespace OutRunVR::StereoCompletion
{
    constexpr bool CanPublishStereoDraw(
        bool leftSucceeded, bool rightSucceeded, bool restored) noexcept
    {
        return leftSucceeded && rightSucceeded && restored;
    }

    static_assert(CanPublishStereoDraw(true, true, true));
    static_assert(!CanPublishStereoDraw(false, true, true));
    static_assert(!CanPublishStereoDraw(true, false, true));
    static_assert(!CanPublishStereoDraw(true, true, false));
    static_assert(!CanPublishStereoDraw(false, false, false));
}
