#include "live_game_sm3_depth_output.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    static_assert(native_sm3_depth_only_pass(true,true,0u,true,true,true,false,false));
    static_assert(!native_sm3_depth_only_pass(false,true,0u,true,true,true,false,false));
    static_assert(!native_sm3_depth_only_pass(true,false,0u,true,true,true,false,false));
    static_assert(!native_sm3_depth_only_pass(true,true,1u,true,true,true,false,false));
    static_assert(!native_sm3_depth_only_pass(true,true,15u,true,true,true,false,false));
    static_assert(!native_sm3_depth_only_pass(true,true,0u,false,true,true,false,false));
    static_assert(!native_sm3_depth_only_pass(true,true,0u,true,false,true,false,false));
    static_assert(!native_sm3_depth_only_pass(true,true,0u,true,true,false,false,false));
    static_assert(!native_sm3_depth_only_pass(true,true,0u,true,true,true,true,false));
    static_assert(!native_sm3_depth_only_pass(true,true,0u,true,true,true,false,true));
    assert(native_sm3_depth_only_pass(true,true,0u,true,true,true,false,false));
}
