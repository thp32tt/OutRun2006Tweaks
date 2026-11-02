// QuestCockpitV2: original Quest Draw::disp_514c30 W * C contract.
// Strict PC event 362 work-pointer owner; NOT a character ID or guessed workId.
// The guest model work is lent to synchronous native draw only and restored.
#pragma once
#include "quest_cockpit_v2_runtime.hpp"
#include <cmath>
#include <cstdint>
namespace OutRunVR::QuestCockpitV2 {
inline bool VerifiedDriverWorkOwner(std::uintptr_t currentWork,
                                    std::uintptr_t slot362Work) noexcept {
    // Quest native event array slot[362].work_token (0x5A8C in native host
    // event array, NOT guest RAM). PC guest live cell 0x79F010 mirrors it.
    return currentWork != 0 && slot362Work != 0 &&
           currentWork == slot362Work;
}
inline bool OriginalOccupantRightCompose(const Matrix& W,const Matrix& C,
                                        Matrix& output) noexcept {
    if(!FiniteAffine(W)||!FiniteAffine(C))return false;
    Matrix result{};
    for(int r=0;r<4;++r){
        for(int c=0;c<4;++c){
            double sum=0.0;
            for(int k=0;k<4;++k)
                sum += static_cast<double>(W[4*r+k])*
                       static_cast<double>(C[4*k+c]);
            if(!std::isfinite(sum))return false;
            result[4*r+c]=static_cast<float>(sum);
        }
    }
    if(!FiniteAffine(result))return false;
    output=result;
    return true;
}
// Production callsite may be admitted ONLY on exact original PC player
// event-362 work pointer, and inside one native renderer game-frame with
// a currently latched stereo pose. The combined game-frame <-> XR
// equivalence still requires headset evidence. No stale pose reuse.
inline bool OriginalOccupantPreviewEligible(bool cockpitEnabled,
    bool nativeViewOne,bool originalPlayerWork,bool originalFrameActive,
    bool xrStereoPoseLatched,bool sceneEffect) noexcept {
    return cockpitEnabled && nativeViewOne && originalPlayerWork &&
           originalFrameActive && xrStereoPoseLatched && !sceneEffect;
}
}
