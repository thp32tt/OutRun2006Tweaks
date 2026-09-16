#pragma once

// R26/R27 Quest/VDXR theater recenter bridge.
//
// Runtime reference-space changes and focus-return events continue to normalize
// into the existing LOCAL theater-anchor invalidation path. R27 additionally
// consumes the explicit F10 request published by the 32-bit game hook, so menu
// theater recenter no longer depends on a runtime-generated OpenXR event.

#include <openxr/openxr.h>
#include "vr/ipc/recenter_request.hpp"

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
    inline std::uint64_t GameRequestsDelivered = 0;
    inline bool FirstReferenceChangeLogged = false;
    inline bool FirstFocusRecenterLogged = false;

    inline void WriteSyntheticLocalChange(XrEventDataBuffer* eventData,
        XrSession session) noexcept
    {
        XrEventDataReferenceSpaceChangePending synthetic{
            XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING };
        synthetic.session = session;
        synthetic.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL;
        synthetic.changeTime = 0;
        synthetic.poseValid = XR_FALSE;
        std::memset(eventData, 0, sizeof(*eventData));
        std::memcpy(eventData, &synthetic, sizeof(synthetic));
    }

    inline XrResult XRAPI_CALL PollEvent(XrInstance instance,
        XrEventDataBuffer* eventData) noexcept
    {
        if (eventData)
        {
            LONG requestId = 0;
            DWORD requesterPid = 0;
            auto& channel = OutRunVR::RecenterIpc::SharedChannel();
            if (channel.Pending(requestId, requesterPid))
            {
                // The host main loop only needs LOCAL + changeTime=0. It will
                // invalidate compositor.theaterAnchor_ before the next frame and
                // EnsureTheaterAnchor will rebuild it from the current HMD pose.
                WriteSyntheticLocalChange(eventData, XR_NULL_HANDLE);
                channel.MarkReceived(requestId);
                channel.MarkApplied(requestId);
                ++GameRequestsDelivered;
                std::cerr
                    << "[R27 recenter] F10 request received requestId="
                    << requestId << " pid=" << requesterPid
                    << "; LOCAL theater reanchor delivered appliedId="
                    << requestId << "\n";
                return XR_SUCCESS;
            }
        }

        if (PendingFocusRecenter && eventData)
        {
            WriteSyntheticLocalChange(eventData, PendingFocusSession);
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
