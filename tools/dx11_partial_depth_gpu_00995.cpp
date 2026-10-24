#include "../src/vr/d3d11/native_game_source_mutation.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::GameNativeSourceMutation;
int main() {
    assert(GameNativeSourceMutation::mirrors_partial_depth_clear(true,true,true,true,true,true));
    assert(!GameNativeSourceMutation::mirrors_partial_depth_clear(false,true,true,true,true,true));
    assert(!GameNativeSourceMutation::mirrors_partial_depth_clear(true,false,true,true,true,true));
    assert(!GameNativeSourceMutation::mirrors_partial_depth_clear(true,true,false,true,true,true));
    assert(!GameNativeSourceMutation::mirrors_partial_depth_clear(true,true,true,false,true,true));
    assert(!GameNativeSourceMutation::mirrors_partial_depth_clear(true,true,true,true,false,true));
    assert(!GameNativeSourceMutation::mirrors_partial_depth_clear(true,true,true,true,true,false));
}
