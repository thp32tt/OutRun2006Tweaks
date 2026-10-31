#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
float sat(float x) { return x < 0.f ? 0.f : x > 1.f ? 1.f : x; }
float ref(std::uint32_t op,float arg0,float arg1,float arg2) {
    return op == kStage1MultiplyAdd ? sat(arg1 + arg2*arg0) :
           op == kStage1Lerp ? sat(arg0*arg1 + (1.f-arg0)*arg2) : -1.f;
}
bool near(float a,float b) {return std::fabs(a-b)<0.00001f;}
}
int main() {
    constexpr std::array<std::uint32_t,2> ops{kStage1MultiplyAdd,kStage1Lerp};
    constexpr std::array<std::uint32_t,3> sources{kStage1Current,kStage1Diffuse,kStage1Factor};
    constexpr std::array<std::uint32_t,4> flags{0u,kStage1Complement,
        kStage1AlphaReplicate,kStage1Complement|kStage1AlphaReplicate};
    std::uint32_t cases=0u;
    for(auto op:ops)
      for(auto s0:sources)for(auto s1:sources)for(auto s2:sources)
       for(auto f0:flags)for(auto f1:flags)for(auto f2:flags) {
         const auto a=s0|f0,b=s1|f1,c=s2|f2;
         if(!stage1_three_source_supported(op,a,b,c))return 1;
         if(stage1_combiner_supported(op,b,c) || stage1_alpha_supported(op,b,c))return 2;
         if(stage1_three_source_reads_diffuse(op,a,b,c) !=
           (s0==kStage1Diffuse||s1==kStage1Diffuse||s2==kStage1Diffuse))return 3;
         ++cases;
       }
    if(cases!=3456u)return 4;
    for(auto op:ops) {
        if(stage1_three_source_supported(op,2u,kStage1Current,kStage1Factor) ||
           stage1_three_source_supported(op,kStage1Current,5u,kStage1Factor) ||
           stage1_three_source_supported(op,kStage1Current,kStage1Factor,0x40u))return 5;
    }
    if(stage1_three_source_supported(24u,kStage1Current,kStage1Current,kStage1Factor) ||
       stage1_three_source_supported(22u,kStage1Current,kStage1Current,kStage1Factor) ||
       stage1_three_source_supported(7u,kStage1Current,kStage1Current,kStage1Factor))return 6;
    if(!near(ref(25u,.4f,.2f,.5f),.4f) ||
       !near(ref(26u,.4f,.2f,.5f),.38f) ||
       !near(ref(25u,.9f,.9f,.9f),1.f) ||
       !near(ref(26u,1.f,.1f,.9f),.1f))return 7;
    if(!stage1_alpha_supported(kStage1Disable,0xffu,0xffu) ||
       !stage1_alpha_supported(kStage1Add,kStage1Current,kStage1Factor))return 8;
    std::puts("PASS 00705: 3456 3-input stage-1 source/modifier cases and RGB/alpha DX9Ex fallback");
}
