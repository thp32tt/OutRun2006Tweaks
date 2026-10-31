// A failed shader-bound native Draw must never reuse its pre-Draw GPU
// copy as evidence for a later Draw in the same game Present.
#include "../src/vr/d3d11/native_game_raw_draw_pair.hpp"
#include "../src/vr/d3d11/native_game_raw_gpu_capture_epoch.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    NativeRawDrawPair pair;
    NativeRawGpuCaptureEpoch epoch;
    int first = 1, second = 2;
    assert(epoch.can_queue(24u, false));
    pair.arm(24u, &first);
    assert(pair.armed());
    // A failed grouped SM3 native submission abandons the pre-copy.
    pair.reset();
    assert(!pair.consume(24u, &first));
    assert(epoch.can_queue(24u, false)); // no completed copy was queued
    pair.arm(24u, &second);
    assert(!pair.consume(24u, &first));
    assert(!pair.armed()); // wrong resource must not remain pending
    pair.arm(24u, &second);
    assert(!pair.consume(25u, &second)); // wrong Present generation
    pair.arm(24u, &second);
    assert(pair.consume(24u, &second));
    assert(!pair.consume(24u, &second)); // a GPU pair is single-use
    epoch.queued(24u);
    assert(!epoch.can_queue(24u, false)); // at most one pair per frame
    assert(!epoch.can_queue(25u, true));  // in-flight readback fences
    assert(epoch.consume() && !epoch.consume());
    assert(epoch.can_queue(25u, false));  // next game's Present
    return 0;
}
