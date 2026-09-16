#pragma once

// R23 final OpenXR presentation authority.
// A gameplay layer is allowed only when the host loop has committed one stable
// Frame.v2 + image-source + pose/FOV bundle. Classic R19 fallback additionally
// requires the currently published production-capture QPC to be the exact
// capture that was committed with that bundle.

#include "r22_runtime_hardening.hpp"
#include "r23_verified_bundle.hpp"

#ifdef xrEndFrame
#undef xrEndFrame
#endif
#ifdef xrDestroySession
#undef xrDestroySession
#endif

#include <iostream>

namespace OutRunVrR23RuntimeHardening
{
    inline constexpr const char* BuildId = "R23-atomic-verified-source-bundle-20260916";
    inline bool FirstActiveLogged = false;
    inline bool FirstBundleBlockLogged = false;
    inline bool FirstFallbackLogged = false;
    inline bool FirstFallbackSourceMismatchLogged = false;

    inline XrResult SubmitNoLayer(XrSession session,
        const XrFrameEndInfo* endInfo) noexcept
    {
        return OutRunVrR22RuntimeHardening::SubmitNoLayer(session, endInfo);
    }

    inline XrResult XRAPI_CALL EndFrame(XrSession session,
        const XrFrameEndInfo* endInfo)
    {
        if (!FirstActiveLogged)
        {
            FirstActiveLogged = true;
            std::cerr
                << "[R23] final presentation authority ACTIVE build=" << BuildId
                << "; Frame.v2 + source + pose/FOV must be one committed bundle\n";
        }

        if (OutRunVrReviewHardening::HasIncomingNonProjectionLayer(endInfo))
            return OutRunVrFinalTest::EndFrame(session, endInfo);
        if (!OutRunVrR21RuntimeHardening::HostShouldRenderReadonly())
            return OutRunVrFinalTest::EndFrame(session, endInfo);

        OutRunVR::SharedRenderFrameState latest{};
        std::uint32_t publish = 0;
        if (!OutRunVrFinalTest::ReadLatestFrame(latest, publish) ||
            !OutRunVrSbsCaptureOverride::FrameComplete(latest))
            return SubmitNoLayer(session, endInfo);

        const bool direct =
            (latest.flags & OutRunVR::RenderFrameDirectGpuTransport) != 0;
        const auto kind = direct
            ? OutRunVrR23VerifiedBundle::SourceKind::DirectGpu
            : OutRunVrR23VerifiedBundle::SourceKind::ClassicSbs;
        OutRunVrR23VerifiedBundle::Snapshot verified{};
        if (!OutRunVrR23VerifiedBundle::Matches(latest, kind, &verified))
        {
            if (!FirstBundleBlockLogged)
            {
                FirstBundleBlockLogged = true;
                std::cerr
                    << "[R23] gameplay layer blocked: latest Frame.v2 has no exact committed image/pose bundle\n";
            }
            return SubmitNoLayer(session, endInfo);
        }

        if (direct)
        {
            // The R23 host loop already committed this exact direct bundle. Use
            // R22's stronger exact openedFrame==latest.frameId safe-copy path so
            // the first recovered cached slot does not depend on a Ready bit that
            // was published before this frame's successful commit.
            return OutRunVrR22RuntimeHardening::RenderExactDirect(
                session, endInfo, latest);
        }

        if (OutRunVrReviewHardening::IncomingProjectionValid(endInfo))
        {
            if (OutRunVrR22RuntimeHardening::ProjectionMatchesFrame(endInfo, latest))
                return OutRunVrFinalTest::EndFrame(session, endInfo);
            return SubmitNoLayer(session, endInfo);
        }

        // R19 fallback is no longer QPC>=frame guessing. It is legal only while
        // R19 still holds the exact production capture that was committed with
        // this verified classic bundle. A later candidate capture changes the
        // production QPC and automatically invalidates this path.
        const bool exactClassicSource = verified.sourceCaptureQpc > 0 &&
            OutRunVrSbsCaptureOverride::LastProductionPresentQpc ==
                verified.sourceCaptureQpc;
        if (exactClassicSource &&
            OutRunVrReviewHardening::FreshClassicFallbackAvailable())
        {
            OutRunVrR21RuntimeHardening::BindLegacyBlitConstantBufferToVs();
            if (!FirstFallbackLogged)
            {
                FirstFallbackLogged = true;
                std::cerr
                    << "[R23] R19 classic fallback allowed for exact verified source/frame bundle only\n";
            }
            return OutRunVrSbsCaptureOverride::EndFrame(session, endInfo);
        }

        if (!exactClassicSource && !FirstFallbackSourceMismatchLogged)
        {
            FirstFallbackSourceMismatchLogged = true;
            std::cerr
                << "[R23] classic fallback blocked: current production capture is not the committed bundle source\n";
        }
        return OutRunVrFinalTest::EndFrame(session, endInfo);
    }

    inline XrResult XRAPI_CALL DestroySession(XrSession session)
    {
        OutRunVrR23VerifiedBundle::Invalidate();
        return OutRunVrR22RuntimeHardening::DestroySession(session);
    }
}

#define xrEndFrame OutRunVrR23RuntimeHardening::EndFrame
#define xrDestroySession OutRunVrR23RuntimeHardening::DestroySession
