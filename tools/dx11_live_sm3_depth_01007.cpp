#include "live_game_sm3_depth_output.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    static_assert(native_sm3_depth_destination(0u, 1u, false));
    static_assert(!native_sm3_depth_destination(1u, 1u, false));
    static_assert(!native_sm3_depth_destination(0u, 15u, false));
    static_assert(!native_sm3_depth_destination(0u, 1u, true));
    static_assert(native_sm3_depth_target(true, true, true, false, false));
    static_assert(!native_sm3_depth_target(false, true, true, false, false));
    static_assert(!native_sm3_depth_target(true, false, true, false, false));
    static_assert(!native_sm3_depth_target(true, true, false, false, false));
    static_assert(!native_sm3_depth_target(true, true, true, true, false));
    static_assert(!native_sm3_depth_target(true, true, true, false, true));
    assert(native_sm3_depth_target(true, true, true, false, false));
}
