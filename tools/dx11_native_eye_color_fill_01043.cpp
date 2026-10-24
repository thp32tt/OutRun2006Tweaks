#include "../src/vr/d3d11/native_game_color_fill.hpp"
#include <cassert>
using outrun::vr::dx11::native_game_color_fill_clip;
int main() {
    const auto a=native_game_color_fill_clip(3440,1440,false);
    assert(a.valid && a.full && !a.empty);
    const auto b=native_game_color_fill_clip(3440,1440,true,-50,240,350,580);
    assert(b.valid && !b.full && !b.empty);
    assert(b.left==0&&b.top==240&&b.right==350&&b.bottom==580);
    const auto c=native_game_color_fill_clip(3440,1440,true,3200,1300,4000,1600);
    assert(c.right==3440&&c.bottom==1440);
    assert(native_game_color_fill_clip(3440,1440,true,-20,-20,4000,1500).full);
    assert(native_game_color_fill_clip(3440,1440,true,3500,0,3800,50).empty);
    assert(!native_game_color_fill_clip(3440,1440,true,100,0,10,20).valid);
    assert(!native_game_color_fill_clip(0,1440,false).valid);
    assert(!native_game_color_fill_clip(0x80000000u,1440,false).valid);
}
