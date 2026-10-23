#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include "../src/vr/d3d11/live_game_fvf_layout.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::array<std::uint32_t,4> sources{
        kStage1Diffuse, kStage1Current, kStage1Factor, kStage1Specular};
    constexpr std::array<std::uint32_t,4> modifiers{
        0u, kStage1Complement, kStage1AlphaReplicate,
        kStage1Complement | kStage1AlphaReplicate};
    unsigned rgbAlpha = 0, triadic = 0;
    for (auto a : sources) for (auto b : sources)
        for (auto ma : modifiers) for (auto mb : modifiers) {
            if (!stage1_combiner_supported(kStage1Add,a|ma,b|mb) ||
                !stage1_alpha_supported(kStage1Add,a|ma,b|mb) ||
                stage1_operation_reads_specular(kStage1Add,a|ma,b|mb) !=
                (a==kStage1Specular || b==kStage1Specular)) return 1;
            ++rgbAlpha;
        }
    for (auto a : sources) for (auto b : sources) for (auto c : sources)
        for (auto ma : modifiers) for (auto mb : modifiers) for (auto mc : modifiers) {
            if (!stage1_three_source_supported(kStage1Lerp,a|ma,b|mb,c|mc) ||
                stage1_three_source_reads_specular(kStage1Lerp,a|ma,b|mb,c|mc) !=
                (a==kStage1Specular || b==kStage1Specular || c==kStage1Specular))
                return 2;
            ++triadic;
        }
    if (rgbAlpha!=256u || triadic!=4096u ||
        stage1_operation_reads_specular(kStage1SelectArg1,kStage1Current,kStage1Specular) ||
        !stage1_operation_reads_specular(kStage1SelectArg2,kStage1Current,kStage1Specular) ||
        stage1_operation_reads_specular(kStage1Disable,kStage1Specular,kStage1Specular) ||
        stage1_three_source_reads_specular(kStage1Add,kStage1Specular,kStage1Current,kStage1Factor) ||
        stage1_operand_supported(2u) || stage1_operand_supported(5u) ||
        stage1_operand_supported(kStage1Specular|0x40u)) return 3;
    GameFvfLayout layout{};
    constexpr std::uint32_t fvf=kGameFvfXyzRhw | kGameFvfDiffuse |
                                  kGameFvfSpecular | kGameFvfTex1;
    if (!game_fvf_layout(fvf,layout) || !layout.hasSpecular ||
        layout.diffuseOffset!=16u || layout.texcoordOffset!=24u ||
        layout.minStride!=32u) return 4;
    std::array<std::uint8_t,32> vertex{};
    const float rhw[4]={10.f,20.f,0.5f,1.f};
    const float uv[2]={0.125f,0.75f};
    std::memcpy(vertex.data(),rhw,16u);
    const std::uint32_t diffuse=0xff102030u, specular=0x7fa1b2c3u;
    std::memcpy(vertex.data()+16u,&diffuse,4u);
    std::memcpy(vertex.data()+20u,&specular,4u);
    std::memcpy(vertex.data()+24u,uv,8u);
    GameFvfSample sample{};
    if (!game_fvf_decode_vertex(vertex.data(),vertex.size(),layout,sample) ||
        sample.diffuse!=diffuse || sample.specular!=specular ||
        sample.uv[0]!=uv[0] || sample.uv[1]!=uv[1]) return 5;
    GameFvfLayout noSpecular{};
    if (!game_fvf_layout(fvf & ~kGameFvfSpecular,noSpecular)) return 6;
    GameFvfSample absent{};
    if (!game_fvf_decode_vertex(vertex.data(),vertex.size(),noSpecular,absent) ||
        absent.specular!=0u) return 7;
    std::puts("PASS 00706 FVF SPECULAR -> Stage1 RGB+alpha + triadic, missing-field fallback");
    return 0;
}
