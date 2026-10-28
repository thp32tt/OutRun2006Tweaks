// Native GPU source Draw -> queued copy -> Present consumption, C++17 regression.
#include "../src/vr/d3d11/native_game_raw_gpu_capture_epoch.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::NativeRawGpuCaptureEpoch;
int main() {
    NativeRawGpuCaptureEpoch e;
    // Cold-start menu real Draw can queue even at Present serial zero.
    assert(e.can_queue(0u, false));
    e.queued(0u);
    // Repeated game Draws in the same serial cannot silently replace a
    // successful GPU tile; later unsupported/native reset calls do not alter it.
    assert(!e.can_queue(0u, false));
    assert(!e.can_queue(1u, true)); // outstanding async GPU EVENT
    assert(e.consume());
    assert(!e.consume());
    assert(!e.can_queue(0u, false));
    // A new vehicle/race Present may queue a fresh source Draw only after
    // the old GPU copy has retired.
    assert(e.can_queue(1u, false));
    e.queued(1u);
    assert(e.consume());
    // A finished source GPU copy may paint only its matching original
    // Present; a consumed ticket cannot be reused on a second Present.
    e.reset();
    e.queued(7u);
    assert(e.consume_for_present(7u));
    assert(!e.consume_for_present(7u));
    // Once an async copy times out at Present 8, completion at Present 9
    // must discard the old game pixels while preserving in-flight storage.
    e.reset();
    e.queued(8u);
    assert(!e.consume_for_present(9u));
    assert(!e.consume_for_present(8u));
    assert(!e.can_queue(9u, true));
    assert(e.can_queue(9u, false)); // only after GPU fence retired
    e.queued(9u);
    assert(e.consume_for_present(9u));
    e.reset(); // genuine Reset/new D3D9 or D3D11 owner
    assert(e.can_queue(0u, false));
    assert(!e.consume());
    const auto max = (std::numeric_limits<std::uint64_t>::max)();
    // Source serial overflow must fail closed, never release stale samples.
    assert(!e.can_queue(max, true));
    assert(e.can_queue(max, false));
    e.queued(max);
    assert(!e.can_queue(max, false));
    assert(!e.consume_for_present(0u)); // wrapped serial is NOT a match
    return 0;
}
