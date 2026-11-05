#include "live_game_sm3_partial_color.hpp"
#include <cassert>
using outrun::vr::dx11::native_sm3_partial_color_draw_allowed;
int main() {
    // Real game RGB-only fade, alpha-only overlay, and mixed masked writes.
    static_assert(native_sm3_partial_color_draw_allowed(7u,7u,false,false));
    static_assert(native_sm3_partial_color_draw_allowed(8u,8u,false,false));
    static_assert(native_sm3_partial_color_draw_allowed(3u,7u,false,false));
    static_assert(native_sm3_partial_color_draw_allowed(1u,15u,false,true));
    static_assert(native_sm3_partial_color_draw_allowed(7u,15u,true,true));
    static_assert(native_sm3_partial_color_draw_allowed(0u,0u,true,false));
    static_assert(!native_sm3_partial_color_draw_allowed(15u,7u,false,false));
    static_assert(!native_sm3_partial_color_draw_allowed(7u,3u,false,false));
    static_assert(!native_sm3_partial_color_draw_allowed(8u,7u,false,false));
    static_assert(!native_sm3_partial_color_draw_allowed(7u,7u,false,true));
    static_assert(!native_sm3_partial_color_draw_allowed(0u,7u,false,false));
    static_assert(!native_sm3_partial_color_draw_allowed(0u,0u,false,false));
    static_assert(!native_sm3_partial_color_draw_allowed(1u,0u,true,false));
    static_assert(!native_sm3_partial_color_draw_allowed(16u,15u,false,false));
    static_assert(!native_sm3_partial_color_draw_allowed(7u,16u,false,false));
    assert(native_sm3_partial_color_draw_allowed(7u,7u,false,false));
}
