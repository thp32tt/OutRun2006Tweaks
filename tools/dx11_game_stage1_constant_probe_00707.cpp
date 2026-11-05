#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
int main(){
 constexpr std::array<std::uint32_t,5> src{kStage1Diffuse,kStage1Current,kStage1Factor,kStage1Specular,kStage1Constant};
 constexpr std::array<std::uint32_t,4> flags{0u,kStage1Complement,kStage1AlphaReplicate,kStage1Complement|kStage1AlphaReplicate};
 unsigned pairs=0,triadic=0;
 for(auto a:src)for(auto b:src)for(auto fa:flags)for(auto fb:flags){
  auto x=a|fa,y=b|fb;
  if(!stage1_combiner_supported(kStage1Add,x,y)||!stage1_alpha_supported(kStage1Add,x,y)||
     stage1_operation_reads_constant(kStage1Add,x,y)!=(a==kStage1Constant||b==kStage1Constant))return 1;
  ++pairs;
 }
 for(auto op:{kStage1MultiplyAdd,kStage1Lerp})for(auto a:src)for(auto b:src)for(auto c:src)
  for(auto fa:flags)for(auto fb:flags)for(auto fc:flags){
   auto x=a|fa,y=b|fb,z=c|fc;
   if(!stage1_three_source_supported(op,x,y,z)||
      stage1_three_source_reads_constant(op,x,y,z)!=(a==kStage1Constant||b==kStage1Constant||c==kStage1Constant))return 2;
   ++triadic;
  }
 if(pairs!=400u||triadic!=16000u||stage1_operation_reads_constant(kStage1Disable,kStage1Constant,kStage1Constant)||
    stage1_operation_reads_constant(kStage1SelectArg1,kStage1Current,kStage1Constant)||
    stage1_operation_reads_constant(kStage1SelectArg2,kStage1Constant,kStage1Current)||
    !stage1_operation_reads_constant(kStage1SelectArg1,kStage1Constant,kStage1Current)||
    !stage1_operation_reads_constant(kStage1SelectArg2,kStage1Current,kStage1Constant)||
    stage1_three_source_reads_constant(kStage1Add,kStage1Constant,kStage1Current,kStage1Current))return 3;
 for(auto bad:{2u,5u,7u,0x40u,0x46u,0x106u})if(stage1_operand_supported(bad))return 4;
 if(kStage1Factor==kStage1Constant||!stage1_combiner_supported(kStage1Modulate,kStage1Factor,kStage1Constant)||
    stage1_alpha_supported(kStage1Lerp,kStage1Current,kStage1Constant))return 5;
 std::puts("PASS 00707 400 RGB/alpha pairs + 16000 three-operand constant cases and fallback");
 return 0;
}
