#pragma once

// R23 final OpenXR presentation authority.
// A gameplay layer is allowed only when the host loop has committed one stable
// Frame.v2 + image-source + pose/FOV bundle. Once committed, that host-owned
// bundle remains authoritative for its short grace lifetime even if the game
// publishes the next Frame.v2 before xrEndFrame is called.

#include "r22_runtime_hardening.hpp"
#include "r23_verified_bundle.hpp"

#ifdef xrEndFrame
#undef xrEndFrame
#endif
#ifdef xrDestroySession
#undef xrDestroySession
#endif

#include <atomic>
#include <cmath>
#include <iostream>

namespace OutRunVrR23RuntimeHardening
{
    inline constexpr const char* BuildId = "R23-owned-verified-bundle-submit-20260916";
    inline bool FirstActiveLogged = false;
    inline bool FirstBundleBlockLogged = false;
    inline bool FirstFallbackLogged = false;
    inline bool FirstFallbackSourceMismatchLogged = false;
    inline bool FirstDirectSafeReuseLogged = false;

    // Diagnostic publication describing what the final authority actually sent
    // to the OpenXR base path. main_r23 uses this only for delayed pixel logs.
    inline std::atomic<std::uint32_t> LastSubmittedFrameId{ 0 };
    inline std::atomic<std::uint32_t> LastSubmittedKind{
        static_cast<std::uint32_t>(OutRunVrR23VerifiedBundle::SourceKind::None) };
    inline std::atomic<bool> LastSubmittedLayer{ false };
    inline std::atomic<std::uint64_t> SubmissionSerial{ 0 };

    inline void RecordFinalSubmission(std::uint32_t frameId,
        OutRunVrR23VerifiedBundle::SourceKind kind, bool hasLayer) noexcept
    {
        LastSubmittedFrameId.store(frameId, std::memory_order_relaxed);
        LastSubmittedKind.store(static_cast<std::uint32_t>(kind),
            std::memory_order_relaxed);
        LastSubmittedLayer.store(hasLayer, std::memory_order_relaxed);
        SubmissionSerial.fetch_add(1, std::memory_order_release);
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

    inline bool Near(float a, float b, float epsilon = 1.0e-4f) noexcept
    {
        return std::isfinite(a) && std::isfinite(b) &&
            std::fabs(a - b) <= epsilon;
    }

    inline bool IncomingPoseMatchesCommittedFrame(
        const XrFrameEndInfo* endInfo,
        const OutRunVR::SharedRenderFrameState& frame) noexcept
    {
        if (!OutRunVrReviewHardening::IncomingProjectionValid(endInfo))
            return false;
        const auto* projection = reinterpret_cast<const XrCompositionLayerProjection*>(
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

    inline XrResult RenderCommittedDirect(XrSession session,
        const XrFrameEndInfo* endInfo,
        const OutRunVrR23VerifiedBundle::Snapshot& verified)
    {
        using namespace OutRunVrD3D9ExDirectPassthrough;
        const auto kind = OutRunVrR23VerifiedBundle::SourceKind::DirectGpu;
        const auto& frame = verified.frame;

        if (!OutRunVrR21RuntimeHardening::DirectTransportRequested() ||
            !IncomingPoseMatchesCommittedFrame(endInfo, frame))
        {
            RecordFinalSubmission(frame.frameId, kind, false);
            return SubmitNoLayer(session, endInfo);
        }

        const auto state = OutRunVrR21RuntimeHardening::ReadDirectHostStateReadonly();
        if (!OutRunVrR22RuntimeHardening::DirectOpenMatchesLatest(state, frame))
        {
            RecordFinalSubmission(frame.frameId, kind, false);
            return SubmitNoLayer(session, endInfo);
        }

        // Once CopySharedFrameToSafeEyes completed, SafeEye is host-owned and
        // independent of producer ring reuse. Reuse it directly even when the
        // original Frame.v2 slot has already advanced/been overwritten.
        const bool safeAlreadyOwned = SafeFrameId == frame.frameId &&
            SafeEyeSrv[0] && SafeEyeSrv[1];
        if (!safeAlreadyOwned && !EnsureSafeFrame(frame.frameId))
        {
            RecordFinalSubmission(frame.frameId, kind, false);
            return SubmitNoLayer(session, endInfo);
        }
        if (safeAlreadyOwned && !FirstDirectSafeReuseLogged)
        {
            FirstDirectSafeReuseLogged = true;
            std::cerr
                << "[R23] reusing host-owned direct safe-eye bundle after producer advanced; frame="
                << frame.frameId << "\n";
        }

        OutRunVrR21RuntimeHardening::BindLegacyBlitConstantBufferToVs();
        XrCompositionLayerProjection projection{};
        std::array<XrCompositionLayerProjectionView, 2> views{};
        if (!RenderSafeProjection(session, endInfo, projection, views))
        {
            RecordFinalSubmission(frame.frameId, kind, false);
            return SubmitNoLayer(session, endInfo);
        }

        const XrCompositionLayerBaseHeader* layer =
            reinterpret_cast<const XrCompositionLayerBaseHeader*>(&projection);
        XrFrameEndInfo patched = *endInfo;
        patched.layerCount = 1;
        patched.layers = &layer;
        RecordFinalSubmission(frame.frameId, kind, true);
        return OutRunVrFinalTest::EndFrame(session, &patched);
    }

    inline XrResult XRAPI_CALL EndFrame(XrSession session,
        const XrFrameEndInfo* endInfo)
    {
        using OutRunVrR23VerifiedBundle::SourceKind;

        if (!FirstActiveLogged)
        {
            FirstActiveLogged = true;
            std::cerr
                << "[R23] final presentation authority ACTIVE build=" << BuildId
                << "; committed host-owned bundle survives newer producer frames for "
                << OutRunVrR23VerifiedBundle::MaxPresentationAgeMs << "ms\n";
        }

        // Theater/quad is deliberately independent of gameplay Frame.v2 and is
        // passed through unchanged. This also makes its final-submission state
        // observable by the asynchronous output diagnostics.
        if (OutRunVrReviewHardening::HasIncomingNonProjectionLayer(endInfo))
        {
            RecordFinalSubmission(0, SourceKind::None,
                endInfo && endInfo->layerCount > 0);
            return OutRunVrFinalTest::EndFrame(session, endInfo);
        }

        if (!OutRunVrR21RuntimeHardening::HostShouldRenderReadonly())
        {
            RecordFinalSubmission(0, SourceKind::None, false);
            return OutRunVrFinalTest::EndFrame(session, endInfo);
        }

        OutRunVrR23VerifiedBundle::Snapshot verified{};
        if (!OutRunVrR23VerifiedBundle::ReadFresh(verified) ||
            !OutRunVrSbsCaptureOverride::FrameComplete(verified.frame))
        {
            if (!FirstBundleBlockLogged)
            {
                FirstBundleBlockLogged = true;
                std::cerr
                    << "[R23] gameplay layer blocked: no fresh committed host-owned frame/source/pose bundle\n";
            }
            RecordFinalSubmission(0, SourceKind::None, false);
            return SubmitNoLayer(session, endInfo);
        }

        // Do not re-read the producer's latest Frame.v2 here. The game may have
        // legitimately published B after the host committed/rendered A. Bundle A
        // remains valid until its TTL expires or main_r23 invalidates it because
        // of session/reference-space/presentation/source lifetime changes.
        if (verified.kind == SourceKind::DirectGpu)
            return RenderCommittedDirect(session, endInfo, verified);

        if (verified.kind != SourceKind::ClassicSbs)
        {
            RecordFinalSubmission(verified.frameId, verified.kind, false);
            return SubmitNoLayer(session, endInfo);
        }

        if (OutRunVrReviewHardening::IncomingProjectionValid(endInfo))
        {
            if (IncomingPoseMatchesCommittedFrame(endInfo, verified.frame))
            {
                RecordFinalSubmission(verified.frameId, verified.kind, true);
                return OutRunVrFinalTest::EndFrame(session, endInfo);
            }
            RecordFinalSubmission(verified.frameId, verified.kind, false);
            return SubmitNoLayer(session, endInfo);
        }

        // R19 fallback remains tied to the exact production capture committed in
        // this bundle; a later candidate capture changes the QPC and invalidates
        // only this fallback, not an already-rendered incoming projection.
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
                    << "[R23] R19 classic fallback allowed for exact committed source/frame bundle only\n";
            }
            RecordFinalSubmission(verified.frameId, verified.kind, true);
            return OutRunVrSbsCaptureOverride::EndFrame(session, endInfo);
        }

        if (!exactClassicSource && !FirstFallbackSourceMismatchLogged)
        {
            FirstFallbackSourceMismatchLogged = true;
            std::cerr
                << "[R23] classic fallback blocked: current production capture is not the committed bundle source\n";
        }
        RecordFinalSubmission(verified.frameId, verified.kind, false);
        return OutRunVrFinalTest::EndFrame(session, endInfo);
    }

    inline XrResult XRAPI_CALL DestroySession(XrSession session)
    {
        OutRunVrR23VerifiedBundle::Invalidate();
        RecordFinalSubmission(0, OutRunVrR23VerifiedBundle::SourceKind::None, false);
        return OutRunVrR22RuntimeHardening::DestroySession(session);
    }
}

#define xrEndFrame OutRunVrR23RuntimeHardening::EndFrame
#define xrDestroySession OutRunVrR23RuntimeHardening::DestroySession
