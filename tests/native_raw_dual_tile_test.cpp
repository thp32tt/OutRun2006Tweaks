#include "src/vr/d3d11/native_game_raw_dual_tile.hpp"
#include "src/vr/d3d11/native_game_raw_color_transport.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    // Two authenticated GPU source byte orders yield identical displayed
    // D3D9 BGRA pixels, with XRGB opaque and ARGB alpha retained.
    const std::uint8_t nativeRgba[8]{17, 31, 241, 77, 9, 128, 255, 2};
    const std::uint8_t nativeBgra[8]{241, 31, 17, 77, 255, 128, 9, 2};
    std::uint8_t dst[8]{};
    native_raw_copy_to_d3d9_bgra(dst, nativeRgba, 2u,
                                 NativeRawColorByteOrder::Rgba, false);
    for (std::uint32_t i = 0u; i < 8u; ++i)
        assert(dst[i] == nativeBgra[i]);
    native_raw_copy_to_d3d9_bgra(dst, nativeBgra, 2u,
                                 NativeRawColorByteOrder::Bgra, true);
    for (std::uint32_t i = 0u; i < 8u; ++i)
        assert(dst[i] == (i % 4u == 3u ? 255u : nativeBgra[i]));
    native_raw_copy_to_d3d9_bgra(dst, nativeRgba, 2u,
                                 NativeRawColorByteOrder::Rgba, true);
    for (std::uint32_t i = 0u; i < 8u; ++i)
        assert(dst[i] == (i % 4u == 3u ? 255u : nativeBgra[i]));
    NativeRawDualTile t{};
    NativeRawDrawExtent fractional{};
    assert(native_raw_viewport_pixel_extent(3440, 1440,
        166.125f, 80.125f, 1.125f, 0.5f, fractional));
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        fractional, 2u, t));
    assert(t.first.x <= 167u && t.first.x + 256u >= 167u);
    assert(t.first.y <= 80u && t.first.y + 144u >= 80u);
    assert(!native_raw_viewport_pixel_extent(3440, 1440,
        3440.125f, 80.f, 1.f, 50.f, fractional));
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{0,0,3440,1440}, 0, t));
    assert(t.hasSecond);
    assert(t.first.x != t.second.x || t.first.y != t.second.y);
    assert(t.first.x + 256 <= 3440 && t.second.x + 256 <= 3440);
    assert(t.first.y + 144 <= 1440 && t.second.y + 144 <= 1440);
    assert(native_raw_source_tiles_disjoint(t.first, t.second, 256, 144));
    // Real 512x144 menu strip contains two exact disjoint GPU source
    // windows. A center-first sampler alone would falsely miss the pair.
    assert(native_raw_dual_draw_tile(512, 144, 256, 144,
        NativeRawDrawExtent{0, 0, 512, 144}, 0u, t));
    assert(t.hasSecond && t.first.x == 0u && t.second.x == 256u);
    assert(t.first.y == 0u && t.second.y == 0u);
    assert(native_raw_source_tiles_disjoint(t.first, t.second, 256, 144));
    // Regression order: evaluate two authenticated source regions before
    // the deliberate single-tile/no-overlap case changes hasSecond.
    assert(native_raw_choose_second_tile(0, 21, t.hasSecond));
    assert(!native_raw_choose_second_tile(21, 21, t.hasSecond));
    assert(!native_raw_choose_second_tile(21, 0, t.hasSecond));
    // A narrow source raster can intersect multiple nominal tile origins,
    // but the same GPU RGB bytes must NEVER count as two native Draw tiles.
    assert(native_raw_dual_draw_tile(640, 480, 256, 144,
        NativeRawDrawExtent{100, 100, 180, 180}, 0u, t));
    assert(!t.hasSecond);
    assert(!native_raw_source_tiles_disjoint(
        NativeRawTileOrigin{0, 0}, NativeRawTileOrigin{120, 50}, 256, 144));
    assert(native_raw_source_tiles_disjoint(
        NativeRawTileOrigin{0, 0}, NativeRawTileOrigin{256, 20}, 256, 144));
    assert(!native_raw_source_tiles_disjoint(
        NativeRawTileOrigin{0, 0}, NativeRawTileOrigin{1, 1}, 0, 144));
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
