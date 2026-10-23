#include "../src/vr/d3d11/native_game_eye_postpass_coverage.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    constexpr unsigned W = 3440u, H = 1440u;
    const NativeGameOffscreenColorRegion left{0u, 0u, W / 2u, H};
    const NativeGameOffscreenColorRegion right{W / 2u, 0u, W, H};
    const NativeGameOffscreenColorRegion whole{0u, 0u, W, H};
    NativeGameEyeColorChronology eye;
    eye.record_unproven_gpu_postpass(whole, W, H);
    assert(!eye.publication_safe(W, H));
    eye.record_proven_gpu_postpass(left);
    // Critical: after a full unknown eye overwrite, a HALF repaint must
    // not trick full_eye into returning false and publish stale pixels.
    assert(!eye.publication_safe(W, H));
    eye.record_proven_gpu_postpass(right);
    assert(eye.full_postpass_eye(W, H));
    assert(eye.publication_safe(W, H));
    // A new full unknown image is genuinely repaired by two *authored*
    // native TARGET Clear passes, not by faking a new camera postpass.
    eye.record_unproven_gpu_postpass(whole, W, H);
    assert(!eye.publication_safe(W, H));
    eye.record_authored_target_clear(left);
    assert(!eye.publication_safe(W, H));
    eye.record_authored_target_clear(right);
    assert(eye.publication_safe(W, H));
    assert(!eye.full_postpass_eye(W, H));
    // A valid small, independent HUD overlay is not a full eye replacement.
    eye.record_unproven_gpu_postpass({100u, 100u, 200u, 200u}, W, H);
    assert(eye.publication_safe(W, H));
    // Partial authored TARGET Clear removes older postpass proof instead
    // of inventing a fresh real-camera Copy/Stretch coverage.
    eye.record_proven_gpu_postpass(whole);
    assert(eye.full_postpass_eye(W, H));
    eye.record_authored_target_clear({5u, 5u, 6u, 6u});
    assert(!eye.full_postpass_eye(W, H));
    assert(eye.publication_safe(W, H));
    eye.reset_after_full_target_clear();
    // Interleaved unknown half-eye copies together replace the full eye.
    eye.record_unproven_gpu_postpass(left, W, H);
    assert(eye.publication_safe(W, H));
    eye.record_unproven_gpu_postpass(right, W, H);
    assert(!eye.publication_safe(W, H));
    eye.record_authored_target_clear(left);
    assert(!eye.publication_safe(W, H));
    eye.record_authored_target_clear(right);
    assert(eye.publication_safe(W, H));
    // Ledger fragmentation of unknown colors must fail closed, even if
    // subtracting an authentic narrow strip exceeds its fixed capacity.
    eye.reset_after_full_target_clear();
    eye.record_unproven_gpu_postpass(whole, W, H);
    for (unsigned i = 0u; i < 40u; ++i)
        eye.record_authored_target_clear({i * 8u, 4u, i * 8u + 1u, 5u});
    assert(!eye.publication_safe(W, H));
    eye.reset_after_full_target_clear();
    assert(eye.publication_safe(W, H));
    return 0;
}
