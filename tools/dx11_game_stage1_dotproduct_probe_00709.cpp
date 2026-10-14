#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <array>
#include <cmath>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
using Vec = std::array<float,4>;
float sat(float x) { return x < 0.f ? 0.f : x > 1.f ? 1.f : x; }
Vec adjust(Vec v, unsigned flags) {
    if(flags & kStage1AlphaReplicate) v={v[3],v[3],v[3],v[3]};
    if(flags & kStage1Complement)for(auto& x:v)x=1.f-x;
    return v;
}
float dot3(Vec a,Vec b) {
    float s=0.f;for(unsigned i=0;i<3;++i)s+=(a[i]*2.f-1.f)*(b[i]*2.f-1.f);
    return sat(s);
}
bool near(float a,float b){return std::fabs(a-b)<1e-5f;}
int main(){
    constexpr std::array<unsigned,5> sources{kStage1Diffuse,kStage1Current,kStage1Factor,kStage1Specular,kStage1Constant};
    constexpr std::array<unsigned,4> mods{0u,kStage1Complement,kStage1AlphaReplicate,kStage1Complement|kStage1AlphaReplicate};
    unsigned regular=0,temp=0;
    for(auto x:sources)for(auto y:sources)for(auto a:mods)for(auto c:mods){
        if(!stage1_combiner_supported(kStage1DotProduct3,x|a,y|c)||
            stage1_alpha_supported(kStage1DotProduct3,x|a,y|c))return 1;
        ++regular;
    }
    for(auto s:sources)for(auto a:mods)for(auto c:mods){
        const unsigned t=kStage1Temp|a,o=s|c;
        if(!stage1_combiner_supported_with_temp(kStage1DotProduct3,t,o,true)||
           !stage1_combiner_supported_with_temp(kStage1DotProduct3,o,t,true)||
           stage1_combiner_supported_with_temp(kStage1DotProduct3,t,o,false)||
           stage1_combiner_supported_with_temp(kStage1DotProduct3,o,t,false)||
           stage1_alpha_supported_with_temp(kStage1DotProduct3,t,o,true))return 2;
        temp+=2;
    }
    if(regular!=400u||temp!=160u)return 3;
    for(auto bad:{2u,7u,0x41u,0x43u,0x45u}){
        if(stage1_combiner_supported(kStage1DotProduct3,bad,kStage1Current)||
           stage1_combiner_supported_with_temp(kStage1DotProduct3,bad,kStage1Current,true))return 4;
    }
    if(stage1_combiner_supported(22u,kStage1Current,kStage1Factor)||
       stage1_combiner_supported(23u,kStage1Current,kStage1Factor)||
       stage1_alpha_supported(kStage1DotProduct3,kStage1Current,kStage1Factor))return 5;
    const Vec a{.75f,.5f,.25f,.4f}, c{.75f,.5f,.25f,.6f};
    if(!near(dot3(a,c),.5f)||
       !near(dot3(adjust(a,kStage1Complement),c),0.f)||
       !near(dot3(adjust(a,kStage1AlphaReplicate),
                  adjust(c,kStage1AlphaReplicate|kStage1Complement)),.12f)||
       !near(dot3(Vec{1,1,1,1},Vec{1,1,1,1}),1.f)||
       !near(dot3(Vec{1,0,1,1},Vec{0,1,0,1}),0.f))return 6;
    if(!stage1_alpha_supported(kStage1SelectArg1,kStage1Current,kStage1Factor)||
       !stage1_alpha_supported(kStage1Disable,0xffu,0xffu)||
       !stage1_operation_reads_specular(kStage1DotProduct3,kStage1Specular,kStage1Current)||
       !stage1_operation_reads_constant(kStage1DotProduct3,kStage1Constant,kStage1Current)||
       !stage1_operation_reads_diffuse(kStage1DotProduct3,kStage1Diffuse,kStage1Current))return 7;
    std::puts("PASS 00709: 400 RGB + 160 TEMP signed dot-product admissions; alpha/fallback");
}
