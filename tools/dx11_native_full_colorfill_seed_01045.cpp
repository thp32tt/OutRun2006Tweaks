#include "../src/vr/d3d11/native_game_color_fill_seed.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_color_fill.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
using outrun::vr::dx11::native_game_color_fill_retires_draw_batch;
static_assert(native_game_full_color_fill_can_seed(
    true,true,true,true,true,true,true,true,true,true));
static_assert(!native_game_full_color_fill_can_seed(
    true,true,false,true,true,true,true,true,true,true));
int main(){
    for(unsigned reject=0;reject<10;++reject){
        bool p[10]{true,true,true,true,true,true,true,true,true,true};
        p[reject]=false;
        assert(!native_game_full_color_fill_can_seed(
            p[0],p[1],p[2],p[3],p[4],p[5],p[6],p[7],p[8],p[9]));
    }
    const std::uintptr_t game=0x1000u, back=0x2000u, z=0x3000u;
    GameNativeClearColor color{};
    color.record(game,back,0x00772233u,true,true,z);
    assert(color.matches(game,back) && color.main_depth_still_bound(z));
    assert(color.native_color(game,back,{})[3] == 1.0f);
    GameNativeFrameBatch batch{};
    assert(batch.accepts_full_seeded(0u,color.matches(game,back)));
    batch.record_source_draw(0u);
    batch.succeeded(false);
    assert(batch.publishable_full(true,1u));
    assert(native_game_color_fill_retires_draw_batch(true,batch.submitted!=0u));
    batch.abort();
    assert(!batch.publishable_full(true,1u));
    color.discard();
    assert(!color.matches(game,back));
}
