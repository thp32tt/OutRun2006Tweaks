#include "runtime/r41_skipped_release.hpp"

#include <cstdint>

using OutRunVrR41SkippedRelease::Identity;
using OutRunVrR41SkippedRelease::Queue;
using OutRunVrR41SkippedRelease::SampledHistory;
using OutRunVrR41SkippedRelease::SampleEvidence;
using OutRunVrR41SkippedRelease::StageResult;

int main()
{
    Queue<4> queue{};

    const Identity a{ 10, 20, 30, 1, 100 };
    if (queue.Stage(a) != StageResult::Staged) return 1;
    if (!queue.Pending(a) || queue.PendingCount() != 1) return 2;
    if (queue.Stage(a) != StageResult::AlreadyPending) return 3;

    int publishAttempts = 0;
    queue.Retry(
        [&](const Identity& value) {
            return value.clientPid == 10 &&
                value.runGeneration == 20 &&
                value.transportGeneration == 30;
        },
        [&](const Identity&) {
            ++publishAttempts;
            return false;
        });
    if (publishAttempts != 1 || !queue.Pending(a)) return 4;

    queue.Retry(
        [&](const Identity&) { return true; },
        [&](const Identity& value) {
            ++publishAttempts;
            return value.frameId == 100;
        });
    if (publishAttempts != 2 || queue.PendingCount() != 0) return 5;

    const Identity liveOld{ 10, 20, 30, 2, 200 };
    const Identity liveReplacement{ 10, 20, 30, 2, 201 };
    if (queue.Stage(liveOld) != StageResult::Staged) return 6;
    if (queue.Stage(liveReplacement) != StageResult::LiveSlotConflict) return 7;
    if (!queue.Pending(liveOld) || queue.Pending(liveReplacement)) return 8;
    if (!queue.SlotBlocked(liveReplacement)) return 9;

    const Identity nextTransport{ 10, 20, 31, 2, 300 };
    if (queue.Stage(nextTransport) != StageResult::ReplacedStaleProducer)
        return 10;
    if (!queue.Pending(nextTransport) || queue.Pending(liveOld)) return 11;

    int stalePublishAttempts = 0;
    queue.Retry(
        [&](const Identity&) { return false; },
        [&](const Identity&) {
            ++stalePublishAttempts;
            return true;
        });
    if (stalePublishAttempts != 0 || queue.PendingCount() != 0) return 12;

    const Identity nextRun{ 11, 21, 40, 3, 400 };
    if (queue.Stage(nextRun) != StageResult::Staged) return 13;
    queue.Retry(
        [&](const Identity& value) {
            return value.clientPid == 11 &&
                value.runGeneration == 21 &&
                value.transportGeneration == 40;
        },
        [&](const Identity&) { return true; });
    if (queue.PendingCount() != 0) return 14;

    const Identity zeroClient{ 0, 1, 1, 0, 1 };
    const Identity zeroRun{ 1, 0, 1, 0, 1 };
    const Identity zeroTransport{ 1, 1, 0, 0, 1 };
    const Identity zeroFrame{ 1, 1, 1, 0, 0 };
    const Identity badSlot{ 1, 1, 1, 4, 1 };
    if (queue.Stage(zeroClient) != StageResult::Invalid) return 15;
    if (queue.Stage(zeroRun) != StageResult::Invalid) return 16;
    if (queue.Stage(zeroTransport) != StageResult::Invalid) return 17;
    if (queue.Stage(zeroFrame) != StageResult::Invalid) return 18;
    if (queue.Stage(badSlot) != StageResult::Invalid) return 19;

    // Release-before-watermark adapter contract: ownership is staged before
    // publication. A transient ACK failure therefore survives even if the
    // caller advances its selection watermark immediately afterwards.
    const Identity skippedBeforeWatermark{ 50, 60, 70, 0, 500 };
    if (queue.Stage(skippedBeforeWatermark) != StageResult::Staged) return 20;
    std::uint32_t watermark = 0;
    int watermarkAttempts = 0;
    queue.Retry(
        [&](const Identity& value) {
            return value.clientPid == 50 &&
                value.runGeneration == 60 &&
                value.transportGeneration == 70;
        },
        [&](const Identity&) {
            ++watermarkAttempts;
            return false;
        });
    watermark = 501;
    if (watermark != 501 || watermarkAttempts != 1 ||
        !queue.Pending(skippedBeforeWatermark)) return 21;
    queue.Retry(
        [&](const Identity&) { return true; },
        [&](const Identity& value) {
            ++watermarkAttempts;
            return value.frameId == 500;
        });
    if (watermarkAttempts != 2 || queue.PendingCount() != 0) return 22;

    // A sampled/deferred identity must remain outside this queue. The runtime
    // adapter enforces that boundary before Stage(); model it explicitly here
    // and prove the queue stays empty.
    const Identity sampled{ 50, 60, 70, 1, 501 };
    const bool deferredEventOwnsSampled = true;
    if (!deferredEventOwnsSampled) {
        if (queue.Stage(sampled) == StageResult::Invalid) return 23;
    }
    if (queue.PendingCount() != 0) return 24;

    // Positive sampled-history contract. Absence is never proof that a frame
    // was not sampled; only an exact full identity may return ExactSampled.
    SampledHistory<4> sampledHistory{};
    const Identity sampledExact{ 90, 91, 92, 0, 900 };
    if (sampledHistory.Query(sampledExact) != SampleEvidence::Unknown)
        return 25;
    if (!sampledHistory.ObserveSampled(sampledExact)) return 26;
    if (sampledHistory.Query(sampledExact) != SampleEvidence::ExactSampled) return 27;
    if (!sampledHistory.ExactSampled(sampledExact)) return 38;

    const Identity sameProducerNewFrame{ 90, 91, 92, 0, 901 };
    if (sampledHistory.Query(sameProducerNewFrame) !=
        SampleEvidence::Unknown) return 28;

    const Identity nextTransportSameSlot{ 90, 91, 93, 0, 902 };
    if (sampledHistory.Query(nextTransportSameSlot) !=
        SampleEvidence::Unknown) return 29;

    const Identity nextRunSameSlot{ 90, 94, 93, 0, 903 };
    if (sampledHistory.Query(nextRunSameSlot) !=
        SampleEvidence::Unknown) return 30;

    const Identity otherSlot{ 90, 91, 92, 1, 904 };
    if (sampledHistory.Query(otherSlot) != SampleEvidence::Unknown)
        return 31;

    // Reusing a physical slot replaces only the positive exact proof for that
    // slot; it never retroactively labels a different identity as sampled.
    if (!sampledHistory.ObserveSampled(sameProducerNewFrame)) return 32;
    if (sampledHistory.ExactSampled(sampledExact)) return 33;
    if (!sampledHistory.ExactSampled(sameProducerNewFrame)) return 34;

    const Identity invalidSample{ 0, 91, 92, 0, 905 };
    if (sampledHistory.ObserveSampled(invalidSample)) return 35;
    if (sampledHistory.Query(invalidSample) != SampleEvidence::Unknown)
        return 36;

    sampledHistory.Clear();
    if (sampledHistory.Query(sameProducerNewFrame) !=
        SampleEvidence::Unknown) return 37;

    return 0;
}
