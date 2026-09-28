#include "runtime/r41_skipped_release.hpp"

#include <cstdint>

using OutRunVrR41SkippedRelease::Identity;
using OutRunVrR41SkippedRelease::Queue;
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

    return 0;
}
