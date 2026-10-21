#include "../src/vr/d3d11/native_game_offscreen_color_provenance.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11;
using Region = NativeGameOffscreenColorRegion;
constexpr Region whole{0u, 0u, 100u, 80u};
constexpr Region clearUpper = native_game_offscreen_clear_written_region(
    100u, 80u, true, 0, 0, 100, 30);
constexpr Region drawLower{0u, 30u, 100u, 80u};
constexpr Region clearFull = native_game_offscreen_clear_written_region(
    100u, 80u, false, 0, 0, 0, 0);
constexpr auto clearedAndDrawn = std::array<Region, 2u>{clearUpper, drawLower};
static_assert(native_game_offscreen_color_region_fully_covered(
    whole, clearedAndDrawn, clearedAndDrawn.size()));
static_assert(!native_game_offscreen_color_region_fully_covered(
    whole, std::array<Region, 1u>{clearUpper}, 1u));
static_assert(native_game_offscreen_color_region_fully_covered(
    whole, std::array<Region, 1u>{clearFull}, 1u));
// Wrong RTV mip or slice must not authenticate another camera's pixels.
static_assert(!native_game_offscreen_color_key_matches(
    {0x1000u, 0u, 0u}, {0x1000u, 1u, 0u}));
static_assert(!native_game_offscreen_color_key_matches(
    {0x1000u, 0u, 0u}, {0x1000u, 0u, 1u}));
static_assert(!native_game_offscreen_color_region_valid(
    native_game_offscreen_clear_written_region(
        100u, 80u, true, -1, 0, 40, 80)));
static_assert(!native_game_offscreen_color_region_valid(
    native_game_offscreen_clear_written_region(
        100u, 80u, true, 0, 0, 101, 80)));
static_assert(!native_game_offscreen_color_region_valid(
    native_game_offscreen_clear_written_region(
        100u, 80u, true, 0, 0, 0, 80)));
int main() {
    // Actual GPU Clear + Draw can fill a camera before point/linear
    // postpass sampling. A one-pixel hole cannot be promoted to eye color.
    constexpr auto withHole = std::array<Region, 2u>{
        clearUpper, Region{0u, 31u, 100u, 80u}};
    assert(!native_game_offscreen_color_region_fully_covered(
        whole, withHole, withHole.size()));
    constexpr auto clippedCamera = native_game_visible_stretch_sample_region(
        100u, 80u, whole, 100u, 80u, -100, 0, 100, 80, false);
    assert(clippedCamera.left == 50u && clippedCamera.right == 100u);
    assert(native_game_offscreen_color_region_fully_covered(
        clippedCamera, std::array<Region, 1u>{clearFull}, 1u));
}
