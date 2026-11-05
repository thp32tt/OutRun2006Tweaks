#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::array<unsigned,5> src{kStage1Diffuse,kStage1Current,kStage1Factor,kStage1Specular,kStage1Constant};
    constexpr std::array<unsigned,4> mods{0u,kStage1Complement,kStage1AlphaReplicate,kStage1Complement|kStage1AlphaReplicate};
    unsigned regular=0,temp=0,pairs=0;
    for(auto x:src)for(auto y:src)for(auto m:mods)for(auto n:mods) {
        if(!stage1_matched_texture_alpha_blend_supported(kStage1BlendTextureAlphaPM,x|m,y|n,true,false) ||
           stage1_matched_texture_alpha_blend_supported(kStage1BlendTextureAlphaPM,x|m,y|n,false,false) ||
           stage1_combiner_supported(kStage1BlendTextureAlphaPM,x|m,y|n) ||
           stage1_alpha_supported(kStage1BlendTextureAlphaPM,x|m,y|n))return 1;
        ++regular;
    }
    for(auto x:src)for(auto m:mods)for(auto n:mods) {
        if(!stage1_matched_texture_alpha_blend_supported(kStage1BlendTextureAlphaPM,kStage1Temp|m,x|n,true,true) ||
           !stage1_matched_texture_alpha_blend_supported(kStage1BlendTextureAlphaPM,x|n,kStage1Temp|m,true,true) ||
           stage1_matched_texture_alpha_blend_supported(kStage1BlendTextureAlphaPM,kStage1Temp|m,x|n,true,false))return 2;
        temp+=2;
    }
    for(auto c:{kStage1BlendTextureAlpha,kStage1BlendTextureAlphaPM})
        for(auto a:{kStage1BlendTextureAlpha,kStage1BlendTextureAlphaPM}) {
            if(!stage1_matched_texture_alpha_blend_supported(c,kStage1Current,kStage1Factor,true,false) ||
               !stage1_matched_texture_alpha_blend_supported(a,kStage1Factor,kStage1Current,true,false))return 3;
            ++pairs;
        }
    for(auto bad:{2u,7u,0x41u,0x43u,0x45u})
        if(stage1_matched_texture_alpha_blend_supported(kStage1BlendTextureAlphaPM,bad,kStage1Current,true,true))return 4;
    if(stage1_matched_texture_alpha_blend_supported(17u,kStage1Current,kStage1Factor,true,false))return 5;
    for(float weight:{0.f,.25f,.5f,.75f,1.f}) {
        const float arg1=.35f,arg2=.8f;
        const float pm=std::min(1.f,arg1+arg2*(1.f-weight));
        if(std::fabs(pm-std::min(1.f,arg1+arg2-arg2*weight))>1e-5f)return 6;
        if(weight==.5f && std::fabs(pm-(arg1*weight+arg2*(1.f-weight)))<.01f)return 7;
    }
    if(regular!=400u || temp!=160u || pairs!=4u)return 8;
    std::puts("PASS 00711 premultiplied RGB + independent alpha, 560 combos, 4 op pairs and fail-closed fallback");
}
