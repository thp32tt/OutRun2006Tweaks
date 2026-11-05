#include "../src/vr/d3d11/native_game_eye_postpass_coverage.hpp"
#include <cassert>
using namespace outrun::vr::dx11;

int main() {
    constexpr unsigned W = 3440u, H = 1440u;
    NativeGameEyePostpassCoverage eye;
    // Source-proven game Copy then Stretch fill the whole native XR eye.
    eye.record({0u, 0u, 1920u, H});
    eye.record({1920u, 0u, W, H});
    assert(eye.full_eye(W, H));
    // A real subsequent but provenance-unknown camera overlay must remove
    // the overwritten pixels without discarding separate valid screen tiles.
    eye.invalidate({400u, 300u, 900u, 600u});
    assert(!eye.full_eye(W, H));
    eye.record({400u, 300u, 900u, 600u}); // real GPU repaint
    assert(eye.full_eye(W, H));
    // A clipped, partially-out-of-eye Stretch invalidates ONLY the visible
    // portion; an invisible destination and degenerate region are no-ops.
    eye.invalidate({W, 0u, W + 1u, H});
    eye.invalidate({100u, 100u, 100u, 200u});
    assert(eye.full_eye(W, H));
    eye.invalidate({0u, 0u, 1u, 1u});
    assert(!eye.full_eye(W, H));
    eye.record({0u, 0u, 1u, 1u});
    assert(eye.full_eye(W, H));
    // A foreign/unproven full-eye GPU copy replaces ALL previous proof.
    eye.invalidate({0u, 0u, W, H});
    assert(!eye.full_eye(W, H));
    eye.record({0u, 0u, W, H});
    assert(eye.full_eye(W, H));
    // Multiple ordered source operations, including a bridge across two
    // regions, must not treat the gap as game-drawn color.
    eye.reset();
    eye.record({0u, 0u, 100u, 100u});
    eye.invalidate({40u, 0u, 60u, 100u});
    assert(!eye.full_eye(100u, 100u));
    eye.record({40u, 0u, 50u, 100u});
    assert(!eye.full_eye(100u, 100u));
    eye.record({50u, 0u, 60u, 100u});
    assert(eye.full_eye(100u, 100u));
    // A grid of disjoint genuine postpasses can fragment beyond the fixed
    // ledger capacity when overwritten. In that case deny full-eye proof,
    // rather than constructing a bounding box through unknown pixels.
    eye.reset();
    for (unsigned i = 0u; i < 30u; ++i)
        eye.record({i * 4u, 0u, i * 4u + 2u, 10u});
    eye.record({120u, 0u, 160u, 10u});
    eye.invalidate({121u, 2u, 159u, 8u}); // no synthetic full cover
    assert(!eye.full_eye(160u, 10u));
    eye.record({0u, 0u, 160u, 10u}); // genuine replacement restores proof
    assert(eye.full_eye(160u, 10u));
    return 0;
}
