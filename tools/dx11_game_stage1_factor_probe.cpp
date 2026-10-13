#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <cstdint>
#include <initializer_list>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    unsigned tested=0;
    for (std::uint32_t op : {kStage1SelectArg1, kStage1SelectArg2,
        kStage1Modulate, kStage1Modulate2X, kStage1Modulate4X,
        kStage1Add, kStage1Subtract, kStage1AddSmooth}) {
        for (std::uint32_t a : {kStage1Current, kStage1Factor}) {
            for (std::uint32_t b : {kStage1Current, kStage1Factor}) {
                if (!stage1_combiner_supported(op,a,b) ||
                    !stage1_alpha_supported(op,a,b) ||
                    (op != kStage1SelectArg2 &&
                     stage1_combiner_supported(op,a | 0x10u,b)) ||
                    (op != kStage1SelectArg1 &&
                     stage1_combiner_supported(op,a,b | 0x20u)))
                    return 1;
                ++tested;
            }
        }
    }
    for (std::uint32_t bad : {0u, 1u, 8u, 9u, 12u, 255u})
        if (stage1_combiner_supported(bad,kStage1Current,kStage1Factor))
            return 2;
    if (!stage1_alpha_supported(kStage1Disable,0xffu,0xffu) ||
         stage1_operand_supported(kStage1Current | 0x20u) ||
         stage1_operand_supported(kStage1Factor | 0x10u))
        return 3;
    std::printf("00673 32 positive stage1 variants, modifiers and fallback: %u PASS\\n", tested);
    return tested == 32u ? 0 : 4;
}
