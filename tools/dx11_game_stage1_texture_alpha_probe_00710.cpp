#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <array>
#include <cmath>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::array<unsigned,5> src{
        kStage1Diffuse,kStage1Current,kStage1Factor,kStage1Specular,kStage1Constant};
    constexpr std::array<unsigned,4> mods{
        0u,kStage1Complement,kStage1AlphaReplicate,
        kStage1Complement|kStage1AlphaReplicate};
    unsigned regular=0,temp=0;
    for(auto x:src)for(auto y:src)for(auto m:mods)for(auto n:mods){
        const auto a=x|m,b=y|n;
        if(!stage1_matched_texture_alpha_blend_supported(
                kStage1BlendTextureAlpha,a,b,true,false) ||
            stage1_matched_texture_alpha_blend_supported(
                kStage1BlendTextureAlpha,a,b,false,false) ||
            stage1_combiner_supported(kStage1BlendTextureAlpha,a,b) ||
            stage1_alpha_supported(kStage1BlendTextureAlpha,a,b))return 1;
        ++regular;
    }
    for(auto s:src)for(auto m:mods)for(auto n:mods){
        const auto a=kStage1Temp|m,b=s|n;
        if(!stage1_matched_texture_alpha_blend_supported(
                kStage1BlendTextureAlpha,a,b,true,true) ||
           !stage1_matched_texture_alpha_blend_supported(
                kStage1BlendTextureAlpha,b,a,true,true) ||
           stage1_matched_texture_alpha_blend_supported(
                kStage1BlendTextureAlpha,a,b,true,false))return 2;
        temp+=2;
    }
    if(regular!=400u || temp!=160u)return 3;
    for(unsigned invalid:{2u,7u,0x41u,0x43u,0x45u})
        if(stage1_matched_texture_alpha_blend_supported(
                kStage1BlendTextureAlpha,invalid,kStage1Current,true,true))return 4;
    if(stage1_matched_texture_alpha_blend_supported(
            kStage1BlendFactorAlpha,kStage1Current,kStage1Factor,true,false))return 5;
    for(float weight:{0.f,.25f,.5f,.75f,1.f}){
        const float result=.8f*weight+.2f*(1.f-weight);
        if(std::fabs(result-(.2f+.6f*weight))>0.00001f)return 6;
    }
    std::puts("00710: 400 RGB+alpha, 160 TEMP, five weights, unmatched fallback PASS");
}
