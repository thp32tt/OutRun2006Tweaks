#include "src/vr/d3d11/native_game_raw_dual_tile.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    NativeRawDualTile t{};
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{0,0,3440,1440}, 0, t));
    assert(t.hasSecond);
    assert(t.first.x != t.second.x || t.first.y != t.second.y);
    assert(t.first.x + 256 <= 3440 && t.second.x + 256 <= 3440);
    assert(t.first.y + 144 <= 1440 && t.second.y + 144 <= 1440);
    assert(native_raw_choose_second_tile(0, 21, t.hasSecond));
    assert(!native_raw_choose_second_tile(21, 21, t.hasSecond));
    assert(!native_raw_choose_second_tile(21, 0, t.hasSecond));
    assert(native_raw_dual_draw_tile(256, 144, 256, 144,
        NativeRawDrawExtent{0,0,256,144}, 3, t));
    assert(!t.hasSecond && !native_raw_choose_second_tile(0, 1, t.hasSecond));
    assert(!native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{100,100,100,200}, 0, t));
    assert(!t.hasSecond);
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{100,100,900,600}, 4, t));
    assert(t.hasSecond);
}
