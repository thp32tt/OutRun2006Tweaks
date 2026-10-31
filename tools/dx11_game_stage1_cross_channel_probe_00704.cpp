#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
float sat(float x) { return x < 0.f ? 0.f : x > 1.f ? 1.f : x; }
float reference(std::uint32_t op, float ar, float aa, float br) {
    switch (op) {
        case kStage1ModulateAlphaAddColor: return sat(ar + aa*br);
        case kStage1ModulateColorAddAlpha: return sat(ar*br + aa);
        case kStage1ModulateInvAlphaAddColor: return sat(ar + (1.f-aa)*br);
        case kStage1ModulateInvColorAddAlpha: return sat((1.f-ar)*br + aa);
        default: return -1.f;
    }
}
bool near(float a,float b) {return std::fabs(a-b)<0.00001f;}
}
int main() {
    constexpr std::array<std::uint32_t,4> ops{
        kStage1ModulateAlphaAddColor, kStage1ModulateColorAddAlpha,
        kStage1ModulateInvAlphaAddColor, kStage1ModulateInvColorAddAlpha};
    constexpr std::array<std::uint32_t,3> src{kStage1Diffuse,kStage1Current,kStage1Factor};
    constexpr std::array<std::uint32_t,4> mods{0u,kStage1Complement,
        kStage1AlphaReplicate,kStage1Complement|kStage1AlphaReplicate};
    std::uint32_t variants=0u;
    for(auto op:ops) {
        for(auto s1:src)for(auto s2:src)for(auto m1:mods)for(auto m2:mods) {
            const auto a=s1|m1,b=s2|m2;
            if(!stage1_combiner_supported(op,a,b) || stage1_alpha_supported(op,a,b))return 1;
            ++variants;
        }
        if(!stage1_alpha_supported(kStage1Add,kStage1Current,kStage1Factor) ||
           !stage1_alpha_supported(kStage1Disable,0xffu,0xffu))return 2;
        if(stage1_combiner_supported(op,2u,kStage1Factor) ||
           stage1_combiner_supported(op,5u,kStage1Factor) ||
           stage1_combiner_supported(op,kStage1Current,0x40u|kStage1Factor))return 3;
        if(!stage1_operation_reads_diffuse(op,kStage1Diffuse,kStage1Factor) ||
           stage1_operation_reads_diffuse(op,kStage1Current,kStage1Factor))return 4;
    }
    if(variants!=576u)return 5;
    constexpr std::array<float,4> expected{0.35f,0.40f,0.55f,0.70f};
    for(std::size_t i=0;i<ops.size();++i)
        if(!near(reference(ops[i],0.2f,0.3f,0.5f),expected[i]))return 6;
    const std::array<float,4> satArg{0.95f,0.95f,0.95f,0.1f};
    const std::array<float,4> satAlpha{0.9f,0.9f,0.1f,0.95f};
    for(std::size_t i=0;i<ops.size();++i)
        if(!near(reference(ops[i],satArg[i],satAlpha[i],0.95f),1.f))return 7;
    if(stage1_combiner_supported(13u,kStage1Current,kStage1Factor) ||
       stage1_combiner_supported(15u,kStage1Current,kStage1Factor) ||
       stage1_combiner_supported(22u,kStage1Current,kStage1Factor))return 8;
    std::puts("PASS 00704: 576 COLOROP source/flag combinations; independent alpha and DX9Ex fallback");
}
