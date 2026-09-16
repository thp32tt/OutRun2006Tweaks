#pragma once

// R26 Quest/VDXR theater recenter bridge.
//
// Some runtimes do not report a user recenter as a LOCAL-only reference-space
// change. The legacy host loop intentionally listened only for LOCAL changes,
// which could leave the theater quad anchored at an old upper-left position.
// Normalize any reference-space-change event to the existing LOCAL reanchor
// path, and queue one synthetic LOCAL change when the session regains FOCUSED.
// The latter covers Quest system-overlay recenter and headset re-wear without
// changing the compositor's established theater-anchor math.

#include <openxr/openxr.h>

#include <cstdint>
#include <cstring>
#include <iostream>

#ifdef xrPollEvent
#undef xrPollEvent
#endif

namespace OutRunVrR26RecenterHardening
{
    inline bool PendingFocusRecenter = false;
    inline XrSession PendingFocusSession = XR_NULL_HANDLE;
    inline std::uint64_t ReferenceChangesNormalized = 0;
    inline std::uint64_t FocusRecentersQueued = 0;
    inline bool FirstReferenceChangeLogged = false;
    inline bool FirstFocusRecenterLogged = false;

    inline XrResult XRAPI_CALL PollEvent(XrInstance instance,
        XrEventDataBuffer* eventData) noexcept
    {
        if (PendingFocusRecenter && eventData)
        {
            XrEventDataReferenceSpaceChangePending synthetic{
                XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING };
            synthetic.session = PendingFocusSession;
            synthetic.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL;
            synthetic.changeTime = 0;
            synthetic.poseValid = XR_FALSE;

            std::memset(eventData, 0, sizeof(*eventData));
            std::memcpy(eventData, &synthetic, sizeof(synthetic));
            PendingFocusRecenter = false;
            PendingFocusSession = XR_NULL_HANDLE;
            return XR_SUCCESS;
        }

        const XrResult result = ::xrPollEvent(instance, eventData);
        if (result != XR_SUCCESS || !eventData)
            return result;

        if (eventData->type == XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING)
        {
            auto* change = reinterpret_cast<XrEventDataReferenceSpaceChangePending*>(
                eventData);

            // The existing host loop already has the correct invalidation and
            // re-anchor path; make every runtime reference-space change enter it.
            change->referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL;
            ++ReferenceChangesNormalized;
            if (!FirstReferenceChangeLogged)
            {
                FirstReferenceChangeLogged = true;
                std::cerr
                    << "[R26 recenter] OpenXR reference-space changes now reanchor the theater regardless of runtime space type\n";
            }
        }
        else if (eventData->type == XR_TYPE_EVENT_DATA_SESSION_STATE_CHANGED)
        {
            const auto* state =
                reinterpret_cast<const XrEventDataSessionStateChanged*>(eventData);
            if (state->state == XR_SESSION_STATE_FOCUSED)
            {
                PendingFocusRecenter = true;
                PendingFocusSession = state->session;
                ++FocusRecentersQueued;
                if (!FirstFocusRecenterLogged)
                {
                    FirstFocusRecenterLogged = true;
                    std::cerr
                        << "[R26 recenter] session FOCUSED queues a theater reanchor for Quest/VDXR recenter and focus return\n";
                }
            }
        }

        return result;
    }
}

#define xrPollEvent OutRunVrR26RecenterHardening::PollEvent
