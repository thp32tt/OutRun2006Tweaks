// RGB GPU evidence must come from a paired original game Draw, not a
// fixed dark-clear constant, alpha-only change or stale source framebuffer.
#include "../src/vr/d3d11/native_game_raw_pixel_delta.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using outrun::vr::dx11::native_raw_rgb_changed;
using outrun::vr::dx11::native_raw_has_rgb_delta;
constexpr bool genuine_source_draw_delta() {
    constexpr std::array<std::uint8_t, 4> dark{{20, 9, 9, 255}};
    constexpr std::array<std::uint8_t, 4> white{{255, 255, 255, 255}};
    constexpr std::array<std::uint8_t, 4> translucent{{20, 9, 9, 10}};
    constexpr std::array<std::uint8_t, 4> tiny{{21, 9, 9, 255}};
    return !native_raw_rgb_changed(dark.data(), dark.data()) &&
           !native_raw_rgb_changed(white.data(), white.data()) &&
           !native_raw_rgb_changed(dark.data(), translucent.data()) &&
           native_raw_rgb_changed(dark.data(), white.data()) &&
           native_raw_rgb_changed(dark.data(), tiny.data()) &&
           native_raw_rgb_changed(white.data(), dark.data());
}
static_assert(genuine_source_draw_delta(), "Only paired RGB changes prove native Draw pixels");
int main() {
    assert(genuine_source_draw_delta());
    // Two rows with four bytes of D3D11 RowPitch padding. Alpha-only
    // mutations permit the later real Draw; a single RGB pixel does not.
    std::array<std::uint8_t, 24> before{}, after{};
    bool changed = true;
    after[3] = 255u;
    assert(native_raw_has_rgb_delta(before.data(), 12u, after.data(),
                                    12u, 2u, 2u, changed) && !changed);
    after[12u + 6u] = 200u;
    assert(native_raw_has_rgb_delta(before.data(), 12u, after.data(),
                                    12u, 2u, 2u, changed) && changed);
    changed = true;
    assert(!native_raw_has_rgb_delta(before.data(), 7u, after.data(),
                                     12u, 2u, 2u, changed) && !changed);
    assert(!native_raw_has_rgb_delta(nullptr, 12u, after.data(),
                                     12u, 2u, 2u, changed));
    return 0;
}
