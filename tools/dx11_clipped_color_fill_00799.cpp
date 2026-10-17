#include "../src/vr/d3d11/native_game_source_mutation.hpp"
#include <cassert>

using namespace outrun::vr::dx11::live_game_frame;
using Mutation = GameNativeSourceMutation;

constexpr bool clipped_game_color_fill_batch() {
    Mutation::ColorFillRect out{};
    using Clip = Mutation::ColorFillClip;
    if (Mutation::classify_color_fill_rect(-20, 10, 40, 70, 100, 80, out)
            != Clip::Pixels ||
        out.left != 0 || out.top != 10 || out.right != 40 || out.bottom != 70)
        return false;
    if (Mutation::classify_color_fill_rect(90, 60, 120, 100, 100, 80, out)
            != Clip::Pixels ||
        out.left != 90 || out.top != 60 || out.right != 100 || out.bottom != 80)
        return false;
    if (Mutation::classify_color_fill_rect(-5, -5, 120, 90, 100, 80, out)
            != Clip::Pixels ||
        out.left != 0 || out.top != 0 || out.right != 100 || out.bottom != 80)
        return false;
    if (Mutation::classify_color_fill_rect(-40, 12, -3, 30, 100, 80, out)
            != Clip::Empty ||
        Mutation::classify_color_fill_rect(101, 12, 110, 30, 100, 80, out)
            != Clip::Empty ||
        Mutation::classify_color_fill_rect(10, 10, 10, 20, 100, 80, out)
            != Clip::Invalid ||
        Mutation::classify_color_fill_rect(10, 20, 12, 18, 100, 80, out)
            != Clip::Invalid ||
        Mutation::classify_color_fill_rect(-1, 0, 2, 5, 0, 80, out)
            != Clip::Invalid ||
        Mutation::classify_color_fill_rect(-1, 0, 2, 5, 0x80000000u, 80, out)
            != Clip::Invalid)
        return false;

    GameNativePreDrawFills batch{};
    if (!batch.record(7, 11, -20, 10, 40, 70, 100, 80, 0xff123456u) ||
        !batch.record(7, 11, 90, 60, 120, 100, 100, 80, 0xff789abcu) ||
        batch.count != 2 || !batch.belongs_to(7, 11) ||
        batch.entries[0].left != 0 || batch.entries[1].right != 100 ||
        batch.entries[1].bottom != 80)
        return false;
    // Offscreen ColorFill does not issue a native GPU command or spend a tile.
    if (!batch.record(7, 11, 120, 30, 150, 40, 100, 80, 0u) ||
        batch.count != 2 || batch.record(7, 99, 0, 0, 10, 10, 100, 80, 0u) ||
        batch.record(7, 11, 10, 20, 0, 30, 100, 80, 0u))
        return false;
    batch.discard();
    return batch.count == 0 && !batch.belongs_to(7, 11);
}
static_assert(clipped_game_color_fill_batch());
int main() { assert(clipped_game_color_fill_batch()); }
