// Regression: sample authentic viewport/scissor (incl clipped game HUD)
// and never sample a wholly off-target region.
#include "../src/vr/d3d11/native_game_raw_draw_tile.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
constexpr bool valid_native_raw_tiles() {
    NativeRawTileOrigin o{};
    if(!native_raw_draw_tile(1920,1080,256,144,{0,0,1920,1080},0,o)||
       o.x!=832u||o.y!=468u) return false;
    for(unsigned i=0;i<5u;++i){
        if(!native_raw_draw_tile(1920,1080,256,144,{1750,60,1850,115},i,o)||
           o.x+256u<=1750u||o.x>=1850u||o.y+144u<=60u||o.y>=115u)
            return false;
    }
    if(!native_raw_draw_tile(640,480,256,144,{-100,-50,7,9},2,o)||
       o.x!=0u||o.y!=0u) return false;
    if(!native_raw_draw_tile(640,480,256,144,{629,471,700,550},4,o)||
       o.x!=384u||o.y!=336u) return false;
    if(native_raw_draw_tile(640,480,256,144,{700,0,710,20},0,o)||
       native_raw_draw_tile(640,480,256,144,{40,20,40,30},0,o)||
       native_raw_draw_tile(250,140,256,144,{0,0,250,140},0,o))
       return false;
    return true;
}
static_assert(valid_native_raw_tiles(),"raw tiles must overlap genuine raster");
int main(){assert(valid_native_raw_tiles());}
