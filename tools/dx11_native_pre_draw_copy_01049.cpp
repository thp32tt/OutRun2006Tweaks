#include "../src/vr/d3d11/native_game_pre_draw_surface.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using outrun::vr::dx11::live_game_frame::GameNativePreDrawSurface;
int main() {
    using S=GameNativePreDrawSurface;
    static_assert(S::capture_allowed(true,true,true,false,false));
    static_assert(!S::capture_allowed(true,false,true,false,false));
    static_assert(!S::capture_allowed(true,true,false,false,false));
    static_assert(!S::capture_allowed(true,true,true,true,false));
    static_assert(!S::capture_allowed(true,true,true,false,true));
    static_assert(S::size_allowed(3440,1440));
    static_assert(!S::size_allowed(0,1440));
    static_assert(!S::size_allowed(65536,65536));
    S s; std::vector<std::uint8_t> original(16u,17u);
    assert(s.record(1,2,2,2,21,original));
    assert(s.matches(1,2,2,2,21));
    assert(!s.matches(2,2,2,2,21));
    assert(!s.matches(1,3,2,2,21));
    assert(!s.matches(1,2,1,4,21));
    assert(!s.matches(1,2,2,2,22));
    original[3]=255;
    assert(s.pixels[3]==17);
    assert(s.record(1,2,2,2,22,original));
    assert(s.pixels[3]==255 && s.matches(1,2,2,2,22));
    assert(!s.record(1,2,3,2,22,original));
    s.discard();
    assert(!s.active() && !s.matches(1,2,2,2,22));
}
