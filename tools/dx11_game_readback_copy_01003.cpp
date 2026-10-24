#include "../src/vr/d3d11/native_game_frame_publication.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::live_game_frame::GameNativeReadbackCopyStamp;
int main() {
    constexpr auto menu = GameNativeReadbackCopyStamp::capture(3440,1440,27);
    constexpr auto car = GameNativeReadbackCopyStamp::capture(1920,1080,28);
    static_assert(menu.valid() && car.valid());
    static_assert(menu.matches(3440,1440,27));
    static_assert(!menu.matches(3440,1440,28));
    static_assert(!menu.matches(1920,1080,27));
    static_assert(!menu.matches(3440,1080,27));
    static_assert(menu.map_pitch_valid(13760));
    static_assert(!menu.map_pitch_valid(13759));
    static_assert(!GameNativeReadbackCopyStamp::capture(0,1440,27).valid());
    static_assert(!GameNativeReadbackCopyStamp::capture(3440,0,27).valid());
    static_assert(!GameNativeReadbackCopyStamp::capture(3440,1440,0).valid());
    static_assert(!GameNativeReadbackCopyStamp::capture(
        (std::numeric_limits<std::uint32_t>::max)(),1,27).valid());
    assert(menu.map_pitch_valid(14080));
    assert(!menu.matches(car.width,car.height,car.generation));
}
