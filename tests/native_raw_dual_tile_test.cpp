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
    // A source color fill that only overlaps the alternate GPU tile
    // must revoke the entire pair. Unknown/full writes remain fail closed.
    constexpr NativeRawSourcePixelRect onlySecond[] = {{500, 500, 650, 650}};
    constexpr NativeRawSourcePixelRect noHit[] = {{0, 0, 80, 80}};
    constexpr NativeRawSourcePixelRect onlyFirst[] = {{105, 105, 140, 140}};
    assert(native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, onlySecond, 1));
    assert(native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, onlyFirst, 1));
    assert(!native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, noHit, 1));
    assert(!native_raw_dual_source_write_overlaps(
        100, 100, false, 500, 500, 256, 144, onlySecond, 1));
    assert(native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, nullptr, 0));
    assert(native_raw_dual_source_write_overlaps(
        0xffffffffu, 0, true, 500, 500, 256, 144, noHit, 1));
    // Distinct game-visible RAW regions: large desktop supports side by
    // side; narrow menus may use vertical placement; tiny crop fails closed.
    NativeRawPresentTile primary{}, secondary{};
    assert(native_raw_partial_present_tile(800, 450, 0, 0, 800, 450,
                                          256, 144, primary));
    assert(native_raw_secondary_present_tile(primary, 0, 0, 800, 450,
                                             secondary));
    assert(secondary.destinationX + secondary.copyWidth + 8 ==
           primary.destinationX);
    assert(secondary.destinationY == primary.destinationY);
    assert(native_raw_partial_present_tile(300, 440, 0, 0, 300, 440,
                                          256, 144, primary));
    assert(native_raw_secondary_present_tile(primary, 0, 0, 300, 440,
                                             secondary));
    assert(secondary.destinationX == primary.destinationX);
    assert(secondary.destinationY ==
           primary.destinationY + primary.copyHeight + 8);
    assert(native_raw_partial_present_tile(300, 185, 0, 0, 300, 185,
                                          256, 144, primary));
    assert(!native_raw_secondary_present_tile(primary, 0, 0, 300, 185,
                                              secondary));
    assert(!native_raw_secondary_present_tile(
        NativeRawPresentTile{}, 0, 0, 800, 450, secondary));
    assert(!native_raw_secondary_present_tile(
        NativeRawPresentTile{0, 0, 256, 144, -2, 8},
        0, 0, 800, 450, secondary));

}
