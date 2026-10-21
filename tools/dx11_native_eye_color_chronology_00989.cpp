#include "../src/vr/d3d11/native_game_eye_postpass_coverage.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    constexpr unsigned W = 3440u, H = 1440u;
    NativeGameEyeColorChronology eye;
    // A genuine direct native Draw or full D3D9 TARGET Clear supplies scene
    // color, but cannot authenticate a later untracked GPU pixel overwrite.
    assert(eye.publication_safe(W, H));
    eye.record_unproven_gpu_postpass({200u, 100u, 900u, 600u});
    assert(!eye.publication_safe(W, H));
    // A cropped real camera repaint is not proof of a complete eye.
    eye.record_proven_gpu_postpass({200u, 100u, 900u, 600u});
    assert(!eye.publication_safe(W, H));
    assert(!eye.full_postpass_eye(W, H));
    // Adjacent authentic GPU camera tiles restore the complete eye.
    eye.record_proven_gpu_postpass({0u, 0u, 1920u, H});
    eye.record_proven_gpu_postpass({1920u, 0u, W, H});
    assert(eye.full_postpass_eye(W, H));
    assert(eye.publication_safe(W, H));
    // An untracked HUD overlay after full coverage again revokes proof.
    eye.record_unproven_gpu_postpass({320u, 80u, 330u, 90u});
    assert(!eye.full_postpass_eye(W, H));
    assert(!eye.publication_safe(W, H));
    eye.record_proven_gpu_postpass({320u, 80u, 330u, 90u});
    assert(eye.full_postpass_eye(W, H));
    assert(eye.publication_safe(W, H));
    // Full genuine D3D9 TARGET Clear physically replaces every foreign pixel.
    eye.record_unproven_gpu_postpass({0u, 0u, W, H});
    assert(!eye.publication_safe(W, H));
    eye.reset_after_full_target_clear();
    assert(eye.publication_safe(W, H));
    assert(!eye.full_postpass_eye(W, H)); // no invented postpass/Draw
    eye.record_proven_gpu_postpass({0u, 0u, 1u, 1u});
    assert(!eye.full_postpass_eye(W, H));
    assert(eye.publication_safe(W, H)); // separate real Draw/Clear gate
    return 0;
}
