#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <array>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::array<unsigned,5> other{kStage1Diffuse,kStage1Current,kStage1Factor,kStage1Specular,kStage1Constant};
    constexpr std::array<unsigned,4> flags{0u,kStage1Complement,kStage1AlphaReplicate,kStage1Complement|kStage1AlphaReplicate};
    constexpr std::array<unsigned,5> ops{kStage1SelectArg1,kStage1SelectArg2,kStage1Modulate,kStage1Add,kStage1AddSigned2X};
    unsigned positive=0,negative=0,three=0;
    for(auto f:flags)for(auto g:flags)for(auto otherArg:other)for(auto op:ops) {
        const unsigned tex=kStage1Texture|f,arg=otherArg|g;
        if(!stage1_matched_texture_two_source_supported(op,tex,arg,true,false,false) ||
           !stage1_matched_texture_two_source_supported(op,tex,arg,true,false,true) ||
            stage1_matched_texture_two_source_supported(op,tex,arg,false,false,false) ||
            stage1_matched_texture_two_source_supported(op,tex,arg,false,false,true))return 1;
        positive+=2;negative+=2;
    }
    for(auto f:flags)for(auto g:flags)for(auto otherArg:other) {
        const unsigned tex=kStage1Texture|f,arg=otherArg|g;
        if(!stage1_matched_texture_three_source_supported(kStage1Lerp,tex,kStage1Factor,arg,true,false) ||
           !stage1_matched_texture_three_source_supported(kStage1MultiplyAdd,arg,tex,kStage1Current,true,false) ||
            stage1_matched_texture_three_source_supported(kStage1MultiplyAdd,arg,tex,kStage1Current,false,false))
            return 2;
        three+=2;
    }
    if(stage1_matched_texture_two_source_supported(kStage1DotProduct3,kStage1Texture,kStage1Current,true,false,true) ||
       stage1_matched_texture_two_source_supported(kStage1Lerp,kStage1Texture,kStage1Current,true,false,false) ||
       stage1_matched_texture_operand_supported(0x42u,true) ||
       stage1_matched_texture_operand_supported(0x82u,true) ||
       stage1_matched_texture_two_source_supported(kStage1Modulate,kStage1Temp,kStage1Texture,true,false,false) ||
       !stage1_matched_texture_two_source_supported(kStage1Modulate,kStage1Temp,kStage1Texture,true,true,false) ||
       !stage1_operation_reads_texture(kStage1SelectArg1,kStage1Texture,kStage1Current) ||
        stage1_operation_reads_texture(kStage1SelectArg1,kStage1Factor,kStage1Texture) ||
       !stage1_three_source_reads_texture(kStage1Lerp,kStage1Factor,kStage1Texture,kStage1Current) ||
        stage1_operation_reads_texture(kStage1Disable,kStage1Texture,kStage1Texture))
        return 3;
    if(positive!=800u || negative!=800u || three!=160u)return 4;
    std::puts("PASS 00712: 800 RGB/alpha matched texture operations, 160 tri-ops, DX9Ex negative fallback");
}
