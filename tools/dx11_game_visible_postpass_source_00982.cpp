#include "../src/vr/d3d11/native_game_offscreen_color_provenance.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11;
using R = NativeGameOffscreenColorRegion;
constexpr R frame{0u, 0u, 100u, 80u};
constexpr R rightHalf{50u, 0u, 100u, 80u};
constexpr R leftHalf{0u, 0u, 50u, 80u};
constexpr auto clippedCopy = native_game_copy_clipped_region(
    100u, 80u, 0u, 0u, 100u, 80u, 100u, 80u, -50, 0);
static_assert(clippedCopy.valid && clippedCopy.sourceLeft == 50u &&
              clippedCopy.sourceRight == 100u && clippedCopy.destX == 0u);
static_assert(native_game_offscreen_color_region_fully_covered(
    rightHalf, std::array<R, 1u>{rightHalf}, 1u));
static_assert(!native_game_offscreen_color_region_fully_covered(
    frame, std::array<R, 1u>{rightHalf}, 1u));
static_assert(!native_game_offscreen_color_region_fully_covered(
    rightHalf, std::array<R, 1u>{leftHalf}, 1u));
int main() {
    const auto point = native_game_visible_stretch_sample_region(
        100u, 80u, frame, 100u, 80u, -100, 0, 100, 80, false);
    assert(point.left == 50u && point.top == 0u &&
           point.right == 100u && point.bottom == 80u);
    assert(native_game_offscreen_color_region_fully_covered(
        point, std::array<R, 1u>{rightHalf}, 1u));
    assert(!native_game_offscreen_color_region_fully_covered(
        point, std::array<R, 1u>{leftHalf}, 1u));
    const auto linear = native_game_visible_stretch_sample_region(
        100u, 80u, frame, 100u, 80u, -100, 0, 100, 80, true);
    assert(linear.left == 49u && linear.right == 100u);
    assert(!native_game_offscreen_color_region_fully_covered(
        linear, std::array<R, 1u>{rightHalf}, 1u));
    assert(native_game_offscreen_color_region_fully_covered(
        linear, std::array<R, 1u>{R{49u, 0u, 100u, 80u}}, 1u));
    const auto full = native_game_visible_stretch_sample_region(
        100u, 80u, frame, 100u, 80u, 0, 0, 100, 80, true);
    assert(full.left == 0u && full.top == 0u &&
           full.right == 100u && full.bottom == 80u);
    const auto gone = native_game_visible_stretch_sample_region(
        100u, 80u, frame, 100u, 80u, 110, 0, 200, 80, false);
    assert(!native_game_offscreen_color_region_valid(gone));
    // Cropped source atlas / mip remains bounded; changing the source crop
    // or filter must not turn foreign texels into same-camera color proof.
    const auto crop = native_game_visible_stretch_sample_region(
        200u, 80u, {20u, 0u, 120u, 80u},
        100u, 80u, -100, 0, 100, 80, false);
    assert(crop.left == 70u && crop.right == 120u);
    assert(!native_game_offscreen_color_key_matches(
        {0x1000u, 1u, 0u}, {0x1000u, 0u, 0u}));
}
