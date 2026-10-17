#include "../src/vr/d3d11/live_game_stage1_dual_texture.hpp"
#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    unsigned positive=0,negative=0;
    for(unsigned b=0;b<64;++b){
        const bool ok=stage1_dual_texture_compatible(
            (b&1)!=0,(b&2)!=0,(b&4)!=0,(b&8)!=0,(b&16)!=0,(b&32)!=0);
        if(ok!=(b==63u))return 1;
        ok?++positive:++negative;
    }
    if(positive!=1||negative!=63)return 2;
    if(!stage1_matched_texture_two_source_supported(
           kStage1Modulate,kStage1Texture,kStage1Current,true,false,false) ||
       !stage1_matched_texture_two_source_supported(
           kStage1Add,kStage1Current,kStage1Texture,true,false,true) ||
       !stage1_matched_texture_three_source_supported(
           kStage1Lerp,kStage1Texture,kStage1Current,kStage1Factor,true,false) ||
       !stage1_matched_texture_two_source_supported(
           kStage1BlendTextureAlphaPM,kStage1Texture,kStage1Current,true,false,true) ||
        stage1_matched_texture_two_source_supported(
           kStage1Add,0x42u,kStage1Current,true,false,true))return 3;
    std::puts("PASS 00713: real dual stage textures, RGB/alpha/PM/LERP, mismatch fallback");
}
