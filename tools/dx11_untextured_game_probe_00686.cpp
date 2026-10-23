#include "../src/vr/d3d11/live_game_fvf_layout.hpp"
#include <cassert>
#include <initializer_list>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    GameFvfLayout f{};
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfDiffuse,f));
    struct Sprite {float p[4]; unsigned rgba;};
    Sprite v{{2.f,3.f,0.5f,1.f},0x81ffccaa};
    GameFvfSample decoded{};
    assert(game_fvf_decode_vertex(&v,sizeof v,f,decoded));
    assert(decoded.diffuse==v.rgba && !f.textured && f.pretransformed);
    assert(game_fvf_untextured_stage0(1,~0u,~0u,4,~0u,~0u,1,true));
    for(unsigned op:{2u,3u})for(unsigned a:{2u,3u})
      for(unsigned arg:{0u,1u})
        assert(game_fvf_untextured_stage0(op,arg,arg,a,arg,arg,1,true));
    assert(!game_fvf_untextured_stage0(1,0,0,4,0,0,4,true));
    assert(!game_fvf_untextured_stage0(1,0,0,4,0,0,1,false));
    assert(!game_fvf_untextured_stage0(2,0,0,1,0,0,1,true));
    assert(!game_fvf_untextured_stage0(2,0x10,0,2,0,0,1,true));
    assert(!game_fvf_untextured_stage0(3,0,0x21,2,0,0,1,true));
    assert(!game_fvf_untextured_stage0(4,0,0,2,0,0,1,true));
}
