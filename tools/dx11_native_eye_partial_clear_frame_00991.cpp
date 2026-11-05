#include "../src/vr/d3d11/native_game_eye_postpass_coverage.hpp"
#include "../src/vr/d3d11/native_game_stereo_draw_evidence.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
using outrun::vr::dx11::live_game_stereo::authored_partial_target_mosaic_eye_ready;
int main() {
    constexpr unsigned W = 3440u, H = 1440u;
    constexpr NativeGameOffscreenColorRegion left{0u, 0u, W / 2u, H};
    constexpr NativeGameOffscreenColorRegion right{W / 2u, 0u, W, H};
    constexpr NativeGameOffscreenColorRegion whole{0u, 0u, W, H};
    NativeGameEyeColorChronology eye;
    eye.record_unproven_gpu_postpass(whole, W, H);
    assert(!eye.publication_safe(W, H));
    eye.record_authored_target_clear(left);
    assert(!eye.full_authored_clear_eye(W, H));
    assert(!eye.publication_safe(W, H));
    eye.record_authored_target_clear(right);
    assert(eye.full_authored_clear_eye(W, H));
    assert(eye.publication_safe(W, H));
    assert(!eye.full_postpass_eye(W, H)); // no invented camera Copy
    // Reject old on-eye geometry, predicated-only and offscreen-only draws.
    assert(!authored_partial_target_mosaic_eye_ready(true, 2, 1, 1, 1));
    assert(!authored_partial_target_mosaic_eye_ready(true, 2, 1, 0, 0));
    assert(!authored_partial_target_mosaic_eye_ready(true, 2, 0, 1, 0));
    assert(!authored_partial_target_mosaic_eye_ready(false, 2, 1, 1, 0));
    assert(authored_partial_target_mosaic_eye_ready(
        eye.full_authored_clear_eye(W, H), 3, 2, 2, 1));
    // Later genuine foreign GPU Copy overwrites half the cleared eye.
    eye.record_unproven_gpu_postpass(left, W, H);
    assert(!eye.full_authored_clear_eye(W, H));
    assert(!authored_partial_target_mosaic_eye_ready(
        eye.full_authored_clear_eye(W, H), 4, 3, 3, 2));
    eye.record_authored_target_clear(left);
    assert(eye.full_authored_clear_eye(W, H));
    assert(eye.publication_safe(W, H));
    // Camera GPU postpass changes physical color; no stale Clear credit.
    eye.record_proven_gpu_postpass(right);
    assert(!eye.full_authored_clear_eye(W, H));
    assert(!eye.full_postpass_eye(W, H));
    eye.reset_after_full_target_clear();
    assert(!eye.full_authored_clear_eye(W, H));
    // Cropped gap, thin HUD overlay, and unfinished tile mosaic fail closed.
    eye.record_authored_target_clear({0u, 0u, W / 2u - 1u, H});
    eye.record_authored_target_clear(right);
    assert(!eye.full_authored_clear_eye(W, H));
    return 0;
}
