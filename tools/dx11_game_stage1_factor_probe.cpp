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
                for (std::uint32_t left : {0u, kStage1Complement,
                                             kStage1AlphaReplicate,
                                             kStage1Complement | kStage1AlphaReplicate}) {
                    for (std::uint32_t right : {0u, kStage1Complement,
                                                kStage1AlphaReplicate,
                                                kStage1Complement | kStage1AlphaReplicate}) {
                        if (!stage1_combiner_supported(op,a | left,b | right) ||
                            !stage1_alpha_supported(op,a | left,b | right))
                            return 1;
                        ++tested;
                    }
                }
            }
        }
    }
    for (std::uint32_t bad : {0u, 1u, 8u, 9u, 12u, 255u})
        if (stage1_combiner_supported(bad,kStage1Current,kStage1Factor))
            return 2;
    if (!stage1_alpha_supported(kStage1Disable,0xffu,0xffu) ||
        !stage1_operand_supported(kStage1Current | kStage1AlphaReplicate) ||
        !stage1_operand_supported(kStage1Factor | kStage1Complement) ||
        !stage1_operand_supported(kStage1Factor | kStage1Complement |
                                 kStage1AlphaReplicate))
        return 3;
    for (std::uint32_t bad : {0u, 2u, 4u, 0x12u, 0x14u, 0x43u, 0x81u, 0x103u})
        if (stage1_operand_supported(bad) ||
            stage1_combiner_supported(kStage1Modulate,kStage1Current,bad))
            return 5;
    std::printf("00700 512 stage1 operand-modified native combinations and fallback: %u PASS\\n", tested);
    return tested == 512u ? 0 : 4;
}
