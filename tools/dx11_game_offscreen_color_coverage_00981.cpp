#include "../src/vr/d3d11/native_game_offscreen_color_provenance.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11;
using R = NativeGameOffscreenColorRegion;

constexpr R whole{0u, 0u, 100u, 80u};
static_assert(native_game_offscreen_color_region_fully_covered(
    whole, std::array<R, 2u>{{{0u, 0u, 50u, 80u},
                              {50u, 0u, 100u, 80u}}}, 2u));
static_assert(native_game_offscreen_color_region_fully_covered(
    whole, std::array<R, 2u>{{{0u, 0u, 100u, 40u},
                              {0u, 40u, 100u, 80u}}}, 2u));
static_assert(native_game_offscreen_color_region_fully_covered(
    whole, std::array<R, 4u>{{{0u, 0u, 50u, 40u},
                              {50u, 0u, 100u, 40u},
                              {0u, 40u, 50u, 80u},
                              {50u, 40u, 100u, 80u}}}, 4u));
static_assert(native_game_offscreen_color_region_fully_covered(
    whole, std::array<R, 2u>{{{0u, 0u, 60u, 80u},
                              {40u, 0u, 100u, 80u}}}, 2u));
static_assert(!native_game_offscreen_color_region_fully_covered(
    whole, std::array<R, 2u>{{{0u, 0u, 49u, 80u},
                              {50u, 0u, 100u, 80u}}}, 2u));
static_assert(!native_game_offscreen_color_region_fully_covered(
    whole, std::array<R, 2u>{{{0u, 0u, 100u, 79u},
                              {0u, 0u, 10u, 80u}}}, 2u));
static_assert(!native_game_offscreen_color_region_fully_covered(
    whole, std::array<R, 2u>{{{99u, 79u, 101u, 81u},
                              {100u, 0u, 110u, 80u}}}, 2u));
static_assert(!native_game_offscreen_color_region_fully_covered(
    whole, std::array<R, 1u>{{{0u, 0u, 100u, 80u}}}, 0u));
static_assert(!native_game_offscreen_color_region_fully_covered(
    whole, std::array<R, 1u>{{{0u, 0u, 100u, 80u}}}, 2u));
static_assert(!native_game_offscreen_color_region_fully_covered(
    {0u, 0u, 0u, 80u},
    std::array<R, 1u>{{{0u, 0u, 100u, 80u}}}, 1u));
static_assert(native_game_offscreen_color_key_matches(
    {0x1000u, 2u, 1u}, {0x1000u, 2u, 1u}));
static_assert(!native_game_offscreen_color_key_matches(
    {0x1000u, 2u, 1u}, {0x1000u, 3u, 1u}));
static_assert(!native_game_offscreen_color_key_matches(
    {0x1000u, 2u, 1u}, {0x1000u, 2u, 0u}));
int main() {
    constexpr std::array<R, 4u> overlapping{{
        {0u, 0u, 60u, 40u}, {40u, 0u, 100u, 40u},
        {0u, 40u, 60u, 80u}, {40u, 40u, 100u, 80u}}};
    assert(native_game_offscreen_color_region_fully_covered(
        whole, overlapping, overlapping.size()));
    assert(!native_game_offscreen_color_region_fully_covered(
        whole, overlapping, 3u));
}
