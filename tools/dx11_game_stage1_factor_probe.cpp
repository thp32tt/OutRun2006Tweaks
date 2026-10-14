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
    // The stage-1 alpha fade family admits op 12/14/16; retain genuinely
    // unsupported operations and source selectors as negative cases.
    for (std::uint32_t bad : {0u, 1u, 13u, 15u, 17u, 255u})
        if (stage1_combiner_supported(bad,kStage1Current,kStage1Factor))
            return 2;
    if (!stage1_alpha_supported(kStage1Disable,0xffu,0xffu) ||
        !stage1_operand_supported(kStage1Current | kStage1AlphaReplicate) ||
        !stage1_operand_supported(kStage1Factor | kStage1Complement) ||
        !stage1_operand_supported(kStage1Factor | kStage1Complement |
                                 kStage1AlphaReplicate))
        return 3;
    for (std::uint32_t bad : {2u, 5u, 6u, 0x12u, 0x15u, 0x43u, 0x81u, 0x103u})
        if (stage1_operand_supported(bad) ||
            stage1_combiner_supported(kStage1Modulate,kStage1Current,bad))
            return 5;
    // Stage1 DIFFUSE is not synonymous with stage0 CURRENT after texture
    // modulation; both RGB and independent alpha can select it with flags.
    unsigned diffuseCases = 0;
    for (std::uint32_t op : {kStage1SelectArg1, kStage1SelectArg2,
        kStage1Modulate, kStage1Modulate2X, kStage1Modulate4X,
        kStage1Add, kStage1Subtract, kStage1AddSmooth}) {
        for (std::uint32_t flags : {0u, kStage1Complement,
            kStage1AlphaReplicate, kStage1Complement | kStage1AlphaReplicate}) {
            const auto d = kStage1Diffuse | flags;
            if (!stage1_combiner_supported(op, d, kStage1Factor) ||
                !stage1_alpha_supported(op, kStage1Factor, d) ||
                stage1_operation_reads_diffuse(op, d, kStage1Factor) !=
                    (op != kStage1SelectArg2) ||
                stage1_operation_reads_diffuse(op, kStage1Factor, d) !=
                    (op != kStage1SelectArg1))
                return 6;
            ++diffuseCases;
        }
    }
    if (stage1_operation_reads_diffuse(kStage1Disable,
                                      kStage1Diffuse, kStage1Diffuse) ||
        stage1_operation_reads_diffuse(kStage1SelectArg1,
                                      kStage1Factor, kStage1Diffuse) ||
        !stage1_operation_reads_diffuse(kStage1SelectArg2,
                                       kStage1Factor, kStage1Diffuse))
        return 7;
    std::printf("00701 stage1 DIFFUSE RGB/alpha ops=%u; prior 00700 variants=%u PASS\\n",
                diffuseCases, tested);
    return tested == 512u ? 0 : 4;
}
