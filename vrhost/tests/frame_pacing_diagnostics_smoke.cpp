#include "vr/ipc/frame_pacing_diagnostics.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace OutRunVR;
int main(int argc, char** argv)
{
    const bool stages = argc > 1 && argv[1][0] == '-' && argv[1][1] == '-'
        && argv[1][2] == 's';
    SharedRenderFrameState frame{};
    frame.frameId = 42;
    frame.presentQpc = 500;
    // The disabled path neither changes IPC data nor emits a buffer entry.
    Pacing::firstGameBeginQpc.store(400);
    Pacing::Buffer off(false);
    Pacing::Sample initial{}; initial.frameId = 42; initial.runGeneration = 7;
    assert(!off.Push(initial) && off.Size() == 0);
    Pacing::StampPublished(frame, 600, true);
    assert(Pacing::ReadQpc(frame, Pacing::BeginLo) == 0);
    // Encoding is ABI-preserving, including QPC values beyond 32 bits.
    Pacing::StoreQpc(frame, Pacing::BeginLo, (1ll << 40) + 200);
    assert(Pacing::ReadQpc(frame, Pacing::BeginLo) == (1ll << 40) + 200);
    assert(Pacing::DurationMs(1000, 2000, 1000000) == 1.0);
    assert(Pacing::DurationMs(2000, 1000, 1000000) < 0);
    assert(Pacing::DurationMs(0, 1000, 1000000) < 0);
    assert(Pacing::DurationMs(1000, 2000, 0) < 0);
    assert(Pacing::DurationMs(1, 20000000, 1000000) < 0);
    Pacing::Buffer buffer(true);
    assert(buffer.Push(initial));
    assert(!buffer.Push(initial)); // duplicate fresh ID
    Pacing::Sample cached = initial; cached.cached = true;
    assert(buffer.Push(cached)); // known cached XR submission
    Pacing::Sample stale = initial; stale.frameId = 41;
    assert(!buffer.Push(stale)); // stale/out-of-order
    assert(!buffer.Push(Pacing::Sample{})); // missing frame and generation
    stale.cached = true;
    assert(!buffer.Push(stale)); // cached ID must match validated predecessor
    Pacing::Sample next = initial; next.frameId = 43;
    assert(buffer.Push(next));
    Pacing::Sample restart = initial; restart.runGeneration = 8;
    assert(buffer.Push(restart)); // new game generation resets identity
    for (std::uint32_t i = 1; i < 270; ++i)
    {
        restart.frameId = 42 + i;
        assert(buffer.Push(restart));
    }
    assert(buffer.Size() == 256 && buffer.Dropped() > 0);
    std::size_t drained = 0;
    buffer.Drain([&](const Pacing::Sample&) { ++drained; });
    assert(drained == 256 && buffer.Size() == 0);
    assert(Pacing::IsNewer(0xfffffffeu, 1u));
    assert(!Pacing::IsNewer(50u, 49u));
    std::cout << (stages ? "PACING-STAGES" : "PACING-REGRESSION")
              << " PASS: IPC QPC, disabled, stale, invalid and bounded buffer\n";
    return 0;
}
