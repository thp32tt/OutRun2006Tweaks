#include "vr/d3d9/r32_policy.hpp"
#include "vr/ipc/direct_history_policy.hpp"

#include <cassert>
#include <cstdint>
#include <limits>

int main()
{
    using namespace OutRunVR::R32;

    // Reset after a long run must not retain an old absolute mono-safety epoch.
    assert(RearmMonoSafetyEpoch(1) == 3);
    assert(RearmMonoSafetyEpoch(42, 2) == 44);
    assert(RearmMonoSafetyEpoch(0, 2) == 3);

    const auto maxValue = (std::numeric_limits<std::uint64_t>::max)();
    assert(RearmMonoSafetyEpoch(maxValue - 1, 4) == maxValue);

    assert(EffectSnapshotResult(true) ==
        EffectSnapshotDecision::UseCapturedPolicy);
    assert(EffectSnapshotResult(false) ==
        EffectSnapshotDecision::ForceZeroDisparity);

    static_assert(ProducerFenceBudgetMs <= 2,
        "R32 producer fence must stay below the old 12 ms synchronous budget");

    // A timed-out D3D9 producer copy cannot make its ring slot reusable until
    // the old EVENT query has actually completed.
    assert(ClassifyPendingFence(false, false, false, false) ==
        PendingFenceDecision::ReuseSlot);
    assert(ClassifyPendingFence(true, true, true, false) ==
        PendingFenceDecision::ReuseSlot);
    assert(ClassifyPendingFence(true, true, false, true) ==
        PendingFenceDecision::BlockReuse);
    assert(ClassifyPendingFence(true, false, false, false) ==
        PendingFenceDecision::QueryError);
    assert(ClassifyPendingFence(true, true, false, false) ==
        PendingFenceDecision::QueryError);

    // R41 stereo-intent epoch: explicit disable and re-enable fallback
    // remain a source barrier until a complete DirectGPU frame from the new
    // intent epoch becomes the authoritative latest publication.
    constexpr std::uint32_t completeDirect =
        OutRunVR::RenderFrameDirectGpuTransport |
        OutRunVR::RenderFrameStereoComplete |
        OutRunVR::RenderFrameWorldStereo |
        OutRunVR::RenderFrameDrawDuplicated |
        OutRunVR::RenderFrameEffectivePoseValid;

    OutRunVR::SharedRenderFrameState oldActive{};
    oldActive.state = OutRunVR::StereoSbsActive;
    oldActive.frameId = 41;
    oldActive.flags = completeDirect;
    oldActive.reserved[OutRunVR::RenderFrameStereoIntentEpochIndex] = 10;

    OutRunVR::SharedRenderFrameState latest{};
    latest.state = OutRunVR::StereoDisabled;
    latest.frameId = 0;
    latest.flags = 0;
    latest.reserved[OutRunVR::RenderFrameStereoIntentEpochIndex] = 11;
    assert(!OutRunVR::DirectHistoryPolicy::
        LatestPublicationAllowsHistory(latest));
    assert(!OutRunVR::DirectHistoryPolicy::
        SameStereoIntentEpoch(oldActive, latest));

    // Re-enable before a fresh color/baseline is ready. FallbackMono belongs to
    // the new epoch and must keep all pre-disable DirectGPU history blocked.
    latest.state = OutRunVR::StereoSbsFallbackMono;
    latest.frameId = 0;
    latest.flags = 0;
    latest.reserved[OutRunVR::RenderFrameStereoIntentEpochIndex] = 12;
    assert(!OutRunVR::DirectHistoryPolicy::
        LatestPublicationAllowsHistory(latest));
    assert(!OutRunVR::DirectHistoryPolicy::
        SameStereoIntentEpoch(oldActive, latest));

    // Only a complete, stable DirectGPU publication from the post-enable epoch
    // opens history again; old epoch descriptors remain ineligible.
    latest.state = OutRunVR::StereoSbsActive;
    latest.frameId = 44;
    latest.flags = completeDirect;
    assert(OutRunVR::DirectHistoryPolicy::
        LatestPublicationAllowsHistory(latest));
    assert(!OutRunVR::DirectHistoryPolicy::
        SameStereoIntentEpoch(oldActive, latest));

    OutRunVR::SharedRenderFrameState freshActive = latest;
    freshActive.frameId = 43;
    assert(OutRunVR::DirectHistoryPolicy::
        SameStereoIntentEpoch(freshActive, latest));

    // An in-flight latest packet is not yet an authority boundary.
    latest.flags = completeDirect | OutRunVR::RenderFramePresentInFlight;
    assert(!OutRunVR::DirectHistoryPolicy::
        LatestPublicationAllowsHistory(latest));

    // Direct-only transient hold emits no new packet. The existing complete
    // active latest publication therefore remains valid and does not create a
    // false disable/re-enable barrier.
    latest.flags = completeDirect;
    assert(OutRunVR::DirectHistoryPolicy::
        LatestPublicationAllowsHistory(latest));

    return 0;
}
