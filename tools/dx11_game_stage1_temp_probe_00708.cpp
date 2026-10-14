#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <cstdio>
#include <initializer_list>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    unsigned pass=0, reject=0;
    // Stage1 RGB/alpha two-input operators with modifiers and all old sources.
    for (auto op : {kStage1SelectArg1,kStage1SelectArg2,kStage1Modulate,
                    kStage1Add,kStage1AddSigned,kStage1BlendCurrentAlpha}) {
        for (auto flags : {0u,kStage1Complement,kStage1AlphaReplicate,
                           kStage1Complement|kStage1AlphaReplicate}) {
            auto temp = kStage1Temp|flags;
            for (auto other : {kStage1Current,kStage1Diffuse,kStage1Factor,
                               kStage1Specular,kStage1Constant}) {
                if (!stage1_combiner_supported_with_temp(op,temp,other,true) ||
                    !stage1_combiner_supported_with_temp(op,other,temp,true) ||
                    !stage1_alpha_supported_with_temp(op,temp,other,true) ||
                    !stage1_alpha_supported_with_temp(op,other,temp,true) ||
                    // SELECTARG2 ignores ARG1; SELECTARG1 ignores ARG2.
                    // An unused TEMP does not require a stage0 producer.
                    stage1_combiner_supported_with_temp(op,temp,other,false) !=
                        (op == kStage1SelectArg2) ||
                    stage1_alpha_supported_with_temp(op,other,temp,false) !=
                        (op == kStage1SelectArg1)) return 1;
                // Four producer-backed positives plus one unused-operand
                // positive for SELECTARG1/2; active TEMP still fails closed.
                const bool unusedTempAllowed =
                    op == kStage1SelectArg1 || op == kStage1SelectArg2;
                pass += unusedTempAllowed ? 5u : 4u;
                reject += unusedTempAllowed ? 1u : 2u;
            }
        }
    }
    // Three-input operation must support TEMP at ARG0, ARG1 or ARG2.
    for (auto op : {kStage1Lerp,kStage1MultiplyAdd}) {
        for (auto flags : {0u,kStage1Complement,kStage1AlphaReplicate,
                           kStage1Complement|kStage1AlphaReplicate}) {
            auto temp=kStage1Temp|flags;
            if (!stage1_three_source_supported_with_temp(op,temp,kStage1Factor,kStage1Diffuse,true) ||
                !stage1_three_source_supported_with_temp(op,kStage1Factor,temp,kStage1Current,true) ||
                !stage1_three_source_supported_with_temp(op,kStage1Current,kStage1Factor,temp,true) ||
                stage1_three_source_supported_with_temp(op,temp,kStage1Factor,kStage1Diffuse,false))
                return 2;
            pass+=3; reject++;
        }
    }
    for (auto bad : {2u,7u,0x45u,0x85u,0x105u}) {
        if (stage1_operand_supported_with_temp(bad,true) ||
            stage1_three_source_supported_with_temp(kStage1Lerp,bad,kStage1Current,kStage1Factor,true))
            return 3;
        reject+=2;
    }
    if (stage1_alpha_supported_with_temp(kStage1ModulateAlphaAddColor,
                                         kStage1Temp,kStage1Current,true) ||
        stage1_combiner_supported_with_temp(kStage1Modulate,
                                            kStage1Temp,kStage1Current,false)) return 4;
    std::printf("Stage0 TEMP -> Stage1 RGB/alpha: pass=%u fallback=%u\n",pass,reject);
    return pass==544u && reject==218u ? 0 : 5;
}
