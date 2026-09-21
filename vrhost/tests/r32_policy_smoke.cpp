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

    // R41 stereo-intent epoch: the latest stable ring snapshot defines
    // which producer epoch may contribute DirectGPU history. Packet state does
    // not shorten the barrier; old epochs remain ineligible across disable and
    // re-enable fallback until a fresh same-epoch active source exists.
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
    latest.reserved[OutRunVR::RenderFrameStereoIntentEpochIndex] = 11;
    assert(OutRunVR::DirectHistoryPolicy::
        LatestPublicationDefinesHistoryEpoch(latest));
    assert(!OutRunVR::DirectHistoryPolicy::
        SameStereoIntentEpoch(oldActive, latest));

    // Re-enable with no fresh baseline: fallback is a newer epoch, so old
    // pre-disable frames remain rejected even though the latest state changed.
    latest.state = OutRunVR::StereoSbsFallbackMono;
    latest.reserved[OutRunVR::RenderFrameStereoIntentEpochIndex] = 12;
    assert(OutRunVR::DirectHistoryPolicy::
        LatestPublicationDefinesHistoryEpoch(latest));
    assert(!OutRunVR::DirectHistoryPolicy::
        SameStereoIntentEpoch(oldActive, latest));

    // Fresh post-enable DirectGPU source carries the new epoch and is eligible.
    OutRunVR::SharedRenderFrameState freshActive{};
    freshActive.state = OutRunVR::StereoSbsActive;
    freshActive.frameId = 43;
    freshActive.flags = completeDirect;
    freshActive.reserved[OutRunVR::RenderFrameStereoIntentEpochIndex] = 12;
    assert(OutRunVR::DirectHistoryPolicy::
        SameStereoIntentEpoch(freshActive, latest));
    assert(!OutRunVR::DirectHistoryPolicy::
        SameStereoIntentEpoch(oldActive, latest));

    // A transient direct-only miss does not change stereo intent. Its in-flight
    // marker stays in the same epoch, so the last safe same-epoch source remains
    // eligible for the existing projection-hold policy.
    latest = freshActive;
    latest.frameId = 44;
    latest.flags = OutRunVR::RenderFramePresentInFlight;
    assert(OutRunVR::DirectHistoryPolicy::
        LatestPublicationDefinesHistoryEpoch(latest));
    assert(OutRunVR::DirectHistoryPolicy::
        SameStereoIntentEpoch(freshActive, latest));

    // Missing epoch metadata fails closed instead of reviving arbitrary history.
    latest.reserved[OutRunVR::RenderFrameStereoIntentEpochIndex] = 0;
    assert(!OutRunVR::DirectHistoryPolicy::
        LatestPublicationDefinesHistoryEpoch(latest));

    return 0;
}
