#pragma once

// R22 final OpenXR presentation guard.
//
// The core compositor may prepare a texture before its second Frame.v2 read has
// proved that metadata stayed stable. R22 therefore treats the final OpenXR
// submission as the transaction boundary: a gameplay projection is submitted
// only when its eye pose/FOV matches the latest complete classic Frame.v2. If
// the producer changed underneath the candidate, the frame is dropped rather
// than pairing an old pose with a newly copied texture. The old QPC-only R19
// gameplay fallback is deliberately not synthesized here.

#include "r21_runtime_hardening.hpp"

#ifdef xrEndFrame
#undef xrEndFrame
#endif
#ifdef xrDestroySession
#undef xrDestroySession
#endif

#include <cmath>
#include <cstdint>
#include <iostream>

namespace OutRunVrR22RuntimeHardening
{
    inline constexpr const char* BuildId =
        "R22-verified-frame-bundle-20260916";

    inline bool FirstActiveLogged = false;
    inline bool FirstBundleRejectLogged = false;
    inline bool FirstClassicFallbackBlockedLogged = false;

    inline bool Near(float a, float b, float epsilon = 1.0e-4f) noexcept
    {
        return std::isfinite(a) && std::isfinite(b) &&
            std::fabs(a - b) <= epsilon;
    }

    inline bool ProjectionMatchesFrame(
        const XrFrameEndInfo* endInfo,
        const OutRunVR::SharedRenderFrameState& frame) noexcept
    {
        if (!OutRunVrReviewHardening::IncomingProjectionValid(endInfo) ||
            frame.state != OutRunVR::StereoSbsActive || !frame.frameId ||
            (frame.flags & OutRunVR::RenderFramePresentInFlight) != 0 ||
            (frame.flags & OutRunVR::RenderFrameDirectGpuTransport) != 0)
            return false;

        constexpr std::uint32_t required =
            OutRunVR::RenderFrameStereoComplete |
            OutRunVR::RenderFrameWorldStereo |
            OutRunVR::RenderFrameDrawDuplicated |
            OutRunVR::RenderFrameEffectivePoseValid;
        if ((frame.flags & required) != required)
            return false;

        const auto* projection =
            reinterpret_cast<const XrCompositionLayerProjection*>(
                endInfo->layers[0]);
        if (!projection || projection->viewCount < 2 || !projection->views)
            return false;

        for (int eye = 0; eye < 2; ++eye)
        {
            const auto& view = projection->views[eye];
            const auto& wire = frame.eye[eye];
            if (!Near(view.pose.orientation.x, wire.orientation[0]) ||
                !Near(view.pose.orientation.y, wire.orientation[1]) ||
                !Near(view.pose.orientation.z, wire.orientation[2]) ||
                !Near(view.pose.orientation.w, wire.orientation[3]) ||
                !Near(view.pose.position.x, wire.position[0]) ||
                !Near(view.pose.position.y, wire.position[1]) ||
                !Near(view.pose.position.z, wire.position[2]) ||
                !Near(view.fov.angleLeft, wire.fov.angleLeft) ||
                !Near(view.fov.angleRight, wire.fov.angleRight) ||
                !Near(view.fov.angleUp, wire.fov.angleUp) ||
                !Near(view.fov.angleDown, wire.fov.angleDown))
                return false;
        }
        return true;
    }

    inline XrResult SubmitNoLayer(XrSession session,
        const XrFrameEndInfo* endInfo) noexcept
    {
        if (!endInfo)
            return OutRunVrFinalTest::EndFrame(session, endInfo);
        XrFrameEndInfo safe = *endInfo;
        safe.layerCount = 0;
        safe.layers = nullptr;
        return OutRunVrFinalTest::EndFrame(session, &safe);
    }

    inline XrResult XRAPI_CALL EndFrame(XrSession session,
        const XrFrameEndInfo* endInfo)
    {
        if (!FirstActiveLogged)
        {
            FirstActiveLogged = true;
            std::cerr
                << "[R22] final verified-frame bundle guard ACTIVE build="
                << BuildId
                << "; gameplay projection requires latest Frame.v2 pose/FOV match; "
                   "QPC-only classic fallback disabled\n";
        }

        // Theater/quad layers are not Frame.v2 gameplay projections.
        if (OutRunVrReviewHardening::HasIncomingNonProjectionLayer(endInfo))
            return OutRunVrFinalTest::EndFrame(session, endInfo);

        // Preserve OpenXR shouldRender/session-visible fail-closed semantics.
        if (!OutRunVrR21RuntimeHardening::HostShouldRenderReadonly())
            return OutRunVrFinalTest::EndFrame(session, endInfo);

        OutRunVR::SharedRenderFrameState latest{};
        std::uint32_t publish = 0;
        const bool haveLatest =
            OutRunVrFinalTest::ReadLatestFrame(latest, publish);

        // Direct frames retain R21's exact openedFrame==latest.frameId staging
        // and host-owned safe-eye copy path.
        if (haveLatest &&
            (latest.flags & OutRunVR::RenderFrameDirectGpuTransport) != 0)
            return OutRunVrR21RuntimeHardening::EndFrame(session, endInfo);

        if (OutRunVrReviewHardening::IncomingProjectionValid(endInfo))
        {
            if (haveLatest && ProjectionMatchesFrame(endInfo, latest))
                return OutRunVrFinalTest::EndFrame(session, endInfo);

            if (!FirstBundleRejectLogged)
            {
                FirstBundleRejectLogged = true;
                std::cerr
                    << "[R22] gameplay projection dropped: incoming pose/FOV is not "
                       "the latest complete classic Frame.v2 bundle; stale pose/new "
                       "texture pairing is fail-closed\n";
            }
            return SubmitNoLayer(session, endInfo);
        }

        // Do not synthesize gameplay projection from only captureQpc >=
        // frame.presentQpc. Without an explicit validated source/frame bundle,
        // dropping the frame is safer than guessing capture identity.
        if (!FirstClassicFallbackBlockedLogged &&
            OutRunVrReviewHardening::FreshClassicFallbackAvailable())
        {
            FirstClassicFallbackBlockedLogged = true;
            std::cerr
                << "[R22] fresh R19 classic capture intentionally not synthesized: "
                   "QPC-only matching cannot prove exact frame/source identity\n";
        }
        return OutRunVrFinalTest::EndFrame(session, endInfo);
    }

    inline XrResult XRAPI_CALL DestroySession(XrSession session)
    {
        return OutRunVrR21RuntimeHardening::DestroySession(session);
    }
}

#define xrEndFrame OutRunVrR22RuntimeHardening::EndFrame
#define xrDestroySession OutRunVrR22RuntimeHardening::DestroySession
