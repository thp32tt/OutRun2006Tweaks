#include "../src/vr/d3d11/live_game_stage1_mirror_reuse.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::stage1_game_mirror_reusable;
int main() {
    // Both real Draw and DrawIndexed use the shared Stage1 native submit.
    // The sampler can be independent while the source view remains shared.
    assert(stage1_game_mirror_reusable(true, true, true, true, true));
    assert(stage1_game_mirror_reusable(true, true, false, false, true));
    // Never reuse another game resource, differing sRGB view, insufficient
    // mip chain or missing Stage0 GPU snapshot: dedicated mirroring remains.
    assert(!stage1_game_mirror_reusable(false, true, true, true, true));
    assert(!stage1_game_mirror_reusable(true, false, true, true, true));
    assert(!stage1_game_mirror_reusable(true, true, true, false, true));
    assert(!stage1_game_mirror_reusable(true, true, false, true, true));
    assert(!stage1_game_mirror_reusable(true, true, true, true, false));
}
