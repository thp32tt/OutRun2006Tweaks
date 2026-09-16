#pragma once

// R24 final visible-presentation guard.
//
// R23 deliberately fails closed to layerCount=0 whenever a verified
// frame/source/pose bundle cannot be proven. That is safe for pose/texture
// ownership, but on a headset it is indistinguishable from a broken renderer.
// R24 keeps the same stereo-safety rules while adding a visible degradation
// ladder:
//   1. preserve validated incoming projection + non-projection layers;
//   2. render DirectGPU only from host-owned SafeEye copies and completion ACK;
//   3. allow a short display-only grace for an already committed bundle;
//   4. fall back to a live theater capture, then to the last released theater/
//      projection swapchain image instead of submitting an empty frame.
//
// The display-only grace never reopens game-side WVP/stereo injection. It only
// prevents a 250ms boundary race from turning a frame that was already rendered
// from a committed source into a black OpenXR frame.

#include "r23_runtime_hardening.hpp"

#ifdef xrEndFrame
#undef xrEndFrame
#endif
#ifdef xrDestroySession
#undef xrDestroySession
#endif

#include <array>
#include <cstdint>
#include <iostream>

namespace OutRunVrR24BlackScreenGuard
{
    inline constexpr const char* BuildId =
        "R24-visible-fallback-final-20260916";
    inline constexpr ULONGLONG DisplayOnlyGraceMs = 500;

    inline std::uint64_t ExactProjectionSubmits = 0;
    inline std::uint64_t SoftGraceProjectionSubmits = 0;
    inline std::uint64_t DirectSafeProjectionSubmits = 0;
    inline std::uint64_t LiveTheaterFallbacks = 0;
    inline std::uint64_t CachedLayerFallbacks = 0;
    inline std::uint64_t EmptyFrameFallbacks = 0;
    inline std::uint64_t MixedValidatedSubmits = 0;

    inline bool FirstExactProjectionLogged = false;
    inline bool FirstSoftGraceLogged = false;
    inline bool FirstDirectSafeLogged = false;
    inline bool FirstLiveTheaterLogged = false;
    inline bool FirstCachedLayerLogged = false;
    inline bool FirstEmptyFallbackLogged = false;
    inline bool FirstMixedValidatedLogged = false;

    struct ProjectionSelection
    {
        const XrCompositionLayerBaseHeader* header = nullptr;
        std::uint32_t count = 0;
    };

    inline ProjectionSelection FindProjection(
        const XrFrameEndInfo* endInfo) noexcept
    {
        ProjectionSelection out{};
        if (!endInfo || !endInfo->layers)
            return out;
        for (std::uint32_t i = 0; i < endInfo->layerCount; ++i)
        {
            const auto* layer = endInfo->layers[i];
            if (layer && layer->type == XR_TYPE_COMPOSITION_LAYER_PROJECTION)
            {
                if (!out.header)
                    out.header = layer;
                ++out.count;
            }
        }
        return out;
    }

    inline bool ProjectionMatchesSnapshot(
        const XrFrameEndInfo* endInfo,
        const OutRunVrR23VerifiedBundle::Snapshot& snapshot) noexcept
    {
        const auto projection = FindProjection(endInfo);
        if (!projection.header || projection.count != 1)
            return false;
        const XrCompositionLayerBaseHeader* oneLayer = projection.header;
        XrFrameEndInfo single = *endInfo;
        single.layerCount = 1;
        single.layers = &oneLayer;
        return OutRunVrR23RuntimeHardening::IncomingPoseMatchesCommittedFrame(
            &single, snapshot.frame);
    }

    inline bool ReadDisplayGraceSnapshot(
        OutRunVrR23VerifiedBundle::Snapshot& out) noexcept
    {
        using namespace OutRunVrR23VerifiedBundle;
        if (!Read(out) || out.kind == SourceKind::None || !out.frameId ||
            out.frame.frameId != out.frameId ||
            out.frame.sourcePoseSequence != out.poseSequence ||
            out.frame.presentQpc != out.presentQpc ||
            !OutRunVrSbsCaptureOverride::FrameComplete(out.frame) ||
            !out.publishedAtMs)
            return false;
        const ULONGLONG now = GetTickCount64();
        return now >= out.publishedAtMs &&
            now - out.publishedAtMs <= DisplayOnlyGraceMs;
    }

    inline XrResult SubmitOriginal(
        XrSession session, const XrFrameEndInfo* endInfo,
        const OutRunVrR23VerifiedBundle::Snapshot& snapshot,
        bool softGrace = false) noexcept
    {
        OutRunVrR23RuntimeHardening::RecordFinalSubmission(
            snapshot.frameId, snapshot.kind, true);
        if (softGrace)
        {
            ++SoftGraceProjectionSubmits;
            if (!FirstSoftGraceLogged)
            {
                FirstSoftGraceLogged = true;
                std::cerr
                    << "[R24] display-only grace accepted an already-rendered committed projection; game-side stereo eligibility remains unchanged build="
                    << BuildId << "\n";
            }
        }
        else
        {
            ++ExactProjectionSubmits;
            if (!FirstExactProjectionLogged)
            {
                FirstExactProjectionLogged = true;
                std::cerr
                    << "[R24] exact committed incoming projection submitted directly; no redundant black-frame gate build="
                    << BuildId << "\n";
            }
        }
        return OutRunVrFinalTest::EndFrame(session, endInfo);
    }

    inline bool TryBuildDirectSafeProjection(
        XrSession session, const XrFrameEndInfo* endInfo,
        const OutRunVrR23VerifiedBundle::Snapshot& snapshot,
        XrCompositionLayerProjection& projection,
        std::array<XrCompositionLayerProjectionView, 2>& views) noexcept
    {
        using namespace OutRunVrD3D9ExDirectPassthrough;
        if (snapshot.kind != OutRunVrR23VerifiedBundle::SourceKind::DirectGpu ||
            !ProjectionMatchesSnapshot(endInfo, snapshot) ||
            !OutRunVrR21RuntimeHardening::DirectTransportRequested())
            return false;

        const auto state =
            OutRunVrR21RuntimeHardening::ReadDirectHostStateReadonly();
        if (!OutRunVrR22RuntimeHardening::DirectOpenMatchesLatest(
                state, snapshot.frame))
            return false;

        const auto generation = snapshot.frame.reserved[
            OutRunVR::RenderFrameDirectGenerationIndex];
        const bool safeAlreadyOwned =
            SafeFrameId == snapshot.frameId &&
            SafeTransportGeneration == generation &&
            SafeEyeSrv[0] && SafeEyeSrv[1];
        if (!safeAlreadyOwned && !EnsureSafeFrame(snapshot.frameId))
            return false;
        if (!OutRunVrR23RuntimeHardening::DirectSafeEyeMatchesCommittedFrame(
                snapshot.frame))
            return false;

        OutRunVrR21RuntimeHardening::BindLegacyBlitConstantBufferToVs();
        return RenderSafeProjection(session, endInfo, projection, views);
    }

    inline XrResult SubmitDirectSafeProjection(
        XrSession session, const XrFrameEndInfo* endInfo,
        const OutRunVrR23VerifiedBundle::Snapshot& snapshot) noexcept
    {
        XrCompositionLayerProjection projection{};
        std::array<XrCompositionLayerProjectionView, 2> views{};
        if (!TryBuildDirectSafeProjection(
                session, endInfo, snapshot, projection, views))
            return XR_ERROR_VALIDATION_FAILURE;

        const XrCompositionLayerBaseHeader* layer =
            reinterpret_cast<const XrCompositionLayerBaseHeader*>(&projection);
        XrFrameEndInfo patched = *endInfo;
        patched.layerCount = 1;
        patched.layers = &layer;
        OutRunVrR23RuntimeHardening::RecordFinalSubmission(
            snapshot.frameId, snapshot.kind, true);
        ++DirectSafeProjectionSubmits;
        if (!FirstDirectSafeLogged)
        {
            FirstDirectSafeLogged = true;
            std::cerr
                << "[R24] DirectGPU final submit uses host-owned SafeEye + per-slot completion ACK; failure now falls back visibly instead of no-layer build="
                << BuildId << "\n";
        }
        return OutRunVrFinalTest::EndFrame(session, &patched);
    }

    inline bool BuildCachedVisibleQuad(
        XrSession session, XrCompositionLayerQuad& quad) noexcept
    {
        using namespace OutRunVrSbsCaptureOverride;
        if (!EnsureViewSpace(session))
            return false;

        XrSwapchain handle = XR_NULL_HANDLE;
        std::uint32_t width = 0;
        std::uint32_t height = 0;
        std::uint32_t arrayIndex = 0;

        if (Theater.handle != XR_NULL_HANDLE && Theater.width && Theater.height)
        {
            handle = Theater.handle;
            width = Theater.width;
            height = Theater.height;
        }
        else if (Projection.handle != XR_NULL_HANDLE &&
            Projection.width && Projection.height)
        {
            handle = Projection.handle;
            width = Projection.width;
            height = Projection.height;
            arrayIndex = 0;
        }
        else
        {
            return false;
        }

        quad = { XR_TYPE_COMPOSITION_LAYER_QUAD };
        quad.space = ViewSpace;
        quad.eyeVisibility = XR_EYE_VISIBILITY_BOTH;
        quad.pose.orientation.w = 1.0f;
        quad.pose.position.z = -1.5f;
        quad.subImage.swapchain = handle;
        quad.subImage.imageRect.offset = { 0, 0 };
        quad.subImage.imageRect.extent = {
            static_cast<std::int32_t>(width),
            static_cast<std::int32_t>(height)
        };
        quad.subImage.imageArrayIndex = arrayIndex;
        const float aspect = height ? static_cast<float>(width) /
            static_cast<float>(height) : (16.0f / 9.0f);
        quad.size.width = 2.0f;
        quad.size.height = 2.0f / std::max(0.5f, aspect);
        return true;
    }

    inline XrResult SubmitVisibleFallback(
        XrSession session, const XrFrameEndInfo* endInfo,
        const char* reason) noexcept
    {
        XrCompositionLayerQuad quad{};
        bool live = OutRunVrSbsCaptureOverride::RenderTheaterOverride(
            session, quad);
        if (!live && !BuildCachedVisibleQuad(session, quad))
        {
            ++EmptyFrameFallbacks;
            if (!FirstEmptyFallbackLogged)
            {
                FirstEmptyFallbackLogged = true;
                std::cerr
                    << "[R24] no live/cached visible fallback exists yet; one empty frame may remain reason="
                    << reason << " build=" << BuildId << "\n";
            }
            OutRunVrR23RuntimeHardening::RecordFinalSubmission(
                0, OutRunVrR23VerifiedBundle::SourceKind::None, false);
            return OutRunVrR23RuntimeHardening::SubmitNoLayer(session, endInfo);
        }

        const XrCompositionLayerBaseHeader* layer =
            reinterpret_cast<const XrCompositionLayerBaseHeader*>(&quad);
        XrFrameEndInfo patched = *endInfo;
        patched.layerCount = 1;
        patched.layers = &layer;
        OutRunVrR23RuntimeHardening::RecordFinalSubmission(
            0, OutRunVrR23VerifiedBundle::SourceKind::None, true);

        if (live)
        {
            ++LiveTheaterFallbacks;
            if (!FirstLiveTheaterLogged)
            {
                FirstLiveTheaterLogged = true;
                std::cerr
                    << "[R24] live theater fallback replaced an unsafe/absent gameplay projection instead of submitting black reason="
                    << reason << " build=" << BuildId << "\n";
            }
        }
        else
        {
            ++CachedLayerFallbacks;
            if (!FirstCachedLayerLogged)
            {
                FirstCachedLayerLogged = true;
                std::cerr
                    << "[R24] cached released OpenXR image preserved visibility while stereo recovers reason="
                    << reason << " build=" << BuildId << "\n";
            }
        }
        return OutRunVrFinalTest::EndFrame(session, &patched);
    }

    inline XrResult XRAPI_CALL EndFrame(
        XrSession session, const XrFrameEndInfo* endInfo) noexcept
    {
        using OutRunVrR23VerifiedBundle::SourceKind;

        if (!endInfo || !OutRunVrR21RuntimeHardening::HostShouldRenderReadonly())
            return OutRunVrR23RuntimeHardening::EndFrame(session, endInfo);

        const auto projection = FindProjection(endInfo);
        const bool hasNonProjection =
            OutRunVrReviewHardening::HasIncomingNonProjectionLayer(endInfo);

        // Theater/menu is already visible and deliberate; do not replace it.
        if (hasNonProjection && projection.count == 0)
        {
            OutRunVrR23RuntimeHardening::RecordFinalSubmission(
                0, SourceKind::None, endInfo->layerCount > 0);
            return OutRunVrFinalTest::EndFrame(session, endInfo);
        }

        OutRunVrR23VerifiedBundle::Snapshot verified{};
        const bool exactBundle =
            OutRunVrR23VerifiedBundle::ReadFresh(verified) &&
            OutRunVrSbsCaptureOverride::FrameComplete(verified.frame);

        // Mixed layers are valid when the single projection independently
        // matches the committed bundle. Preserve the original ordering/content.
        if (hasNonProjection && projection.count == 1 && exactBundle &&
            ProjectionMatchesSnapshot(endInfo, verified))
        {
            ++MixedValidatedSubmits;
            if (!FirstMixedValidatedLogged)
            {
                FirstMixedValidatedLogged = true;
                std::cerr
                    << "[R24] mixed frame preserved after independent projection bundle validation build="
                    << BuildId << "\n";
            }
            OutRunVrR23RuntimeHardening::RecordFinalSubmission(
                verified.frameId, verified.kind, true);
            return OutRunVrFinalTest::EndFrame(session, endInfo);
        }
        if (hasNonProjection)
            return OutRunVrR23RuntimeHardening::SubmitNonProjectionOnly(
                session, endInfo);

        if (exactBundle)
        {
            if (verified.kind == SourceKind::DirectGpu)
            {
                const XrResult direct = SubmitDirectSafeProjection(
                    session, endInfo, verified);
                if (direct != XR_ERROR_VALIDATION_FAILURE)
                    return direct;
                return SubmitVisibleFallback(
                    session, endInfo, "direct-safe-copy/render rejected");
            }

            if (verified.kind == SourceKind::ClassicSbs &&
                ProjectionMatchesSnapshot(endInfo, verified))
                return SubmitOriginal(session, endInfo, verified, false);

            const bool exactClassicSource =
                verified.kind == SourceKind::ClassicSbs &&
                verified.sourceCaptureQpc > 0 &&
                OutRunVrSbsCaptureOverride::LastProductionPresentQpc ==
                    verified.sourceCaptureQpc;
            if (exactClassicSource &&
                OutRunVrReviewHardening::FreshClassicFallbackAvailable())
            {
                OutRunVrR23RuntimeHardening::RecordFinalSubmission(
                    verified.frameId, verified.kind, true);
                return OutRunVrSbsCaptureOverride::EndFrame(session, endInfo);
            }

            return SubmitVisibleFallback(
                session, endInfo, "exact bundle has no safe projection source");
        }

        // If the core rendered a projection just before the 250ms R23 TTL
        // boundary, allow only that already-rendered pose-matched projection for
        // another short interval. No new game-side transform is enabled here.
        OutRunVrR23VerifiedBundle::Snapshot grace{};
        if (ReadDisplayGraceSnapshot(grace) &&
            ProjectionMatchesSnapshot(endInfo, grace))
            return SubmitOriginal(session, endInfo, grace, true);

        // A fresh classic fallback remains preferable to a frozen image.
        if (OutRunVrReviewHardening::FreshClassicFallbackAvailable())
            return OutRunVrSbsCaptureOverride::EndFrame(session, endInfo);

        return SubmitVisibleFallback(
            session, endInfo, "no fresh verified gameplay bundle");
    }

    inline XrResult XRAPI_CALL DestroySession(XrSession session) noexcept
    {
        ExactProjectionSubmits = 0;
        SoftGraceProjectionSubmits = 0;
        DirectSafeProjectionSubmits = 0;
        LiveTheaterFallbacks = 0;
        CachedLayerFallbacks = 0;
        EmptyFrameFallbacks = 0;
        MixedValidatedSubmits = 0;
        return OutRunVrR23RuntimeHardening::DestroySession(session);
    }
}

#define xrEndFrame OutRunVrR24BlackScreenGuard::EndFrame
#define xrDestroySession OutRunVrR24BlackScreenGuard::DestroySession
