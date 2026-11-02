// Quest native Draw::disp_514c30: original robot work W * B0/F0 correction.
// Guest work +0x10 is staged only during the synchronous original PC
// rob_disp_disp_514e60 call; no XR camera, HUD or all-NPC mutation.
// Exact lifetime verified in Quest ELF 0xD61098..0xD612A4.
#pragma once
#include "quest_cockpit_v2_runtime.hpp"
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace OutRunVR::QuestCockpitV2 {
inline bool ComposeOccupantModel(const Matrix& work,
   const Matrix& bodyCorrection, Matrix& destination) noexcept {
    for(float f:work)if(!std::isfinite(f))return false;
    for(float f:bodyCorrection)if(!std::isfinite(f))return false;
    Matrix candidate{};
    for(std::size_t row=0;row<4;++row) {
        for(std::size_t col=0;col<4;++col) {
            double acc=0.;
            for(std::size_t k=0;k<4;++k)
                acc+=double(work[row*4+k])*double(bodyCorrection[k*4+col]);
            candidate[row*4+col]=float(acc);
        }
    }
    for(float f:candidate)if(!std::isfinite(f))return false;
    destination=candidate;
    return true;
}
// Quest render_frame original matrix_F0 16-float identity staging.
 // On Windows the validated player callback can own a synchronous
 // guest-view alias only for the original player car display. This is
 // experimental: original Quest owns the larger renderer frame.
class ScopedOriginalPlayerF0 final {
    float* target_=nullptr;
    Matrix original_{};
public:
    ScopedOriginalPlayerF0(float* target,bool admitted) noexcept {
        if(!target||!admitted)return;
        target_=target;
        std::memcpy(original_.data(),target_,sizeof(Matrix));
        std::memcpy(target_,Identity.data(),sizeof(Matrix));
    }
    ~ScopedOriginalPlayerF0() noexcept {
        if(target_)std::memcpy(target_,original_.data(),sizeof(Matrix));
    }
    ScopedOriginalPlayerF0(const ScopedOriginalPlayerF0&)=delete;
    ScopedOriginalPlayerF0& operator=(const ScopedOriginalPlayerF0&)=delete;
    bool Active()const noexcept{return target_!=nullptr;}
};
inline bool VerifiedPlayerF0CallOwner(bool trial,bool exactPlayerCar,
    bool originalFrameActive,bool nativeCameraMode1,bool xrStereoValid,
    bool sceneEffect,bool reentrant) noexcept {
    return trial&&exactPlayerCar&&originalFrameActive&&nativeCameraMode1&&
           xrStereoValid&&!sceneEffect&&!reentrant;
}
inline bool VerifiedPlayerOccupantScope(bool trial,bool nativeSignature,
    bool activeNativeFrame,bool exactOriginalPlayerRobot,
    bool originalDriverDisplayEntry,bool nativeCameraModeOne,
    bool gameWorld,bool validStereoAndPose,bool sceneEffect) noexcept {
    return trial && nativeSignature && activeNativeFrame &&
        exactOriginalPlayerRobot && originalDriverDisplayEntry &&
        nativeCameraModeOne && gameWorld && validStereoAndPose &&
        !sceneEffect;
}
// Renderer-scoped alias to original robot work only because Windows original
// PC code reads work+0x10 synchronously inside its owned draw. No simulation
// writes survive this call, including C++ exception paths.
class ScopedOriginalRobotWorkMatrix final {
    float* target_ = nullptr;
    Matrix original_{};
public:
    ScopedOriginalRobotWorkMatrix(float* target,const Matrix& corrected,
                                  bool admitted) noexcept {
        if(!admitted||!target)return;
        target_=target;
        std::memcpy(original_.data(),target_,sizeof(Matrix));
        std::memcpy(target_,corrected.data(),sizeof(Matrix));
    }
    ~ScopedOriginalRobotWorkMatrix() noexcept {
        if(target_)std::memcpy(target_,original_.data(),sizeof(Matrix));
    }
    ScopedOriginalRobotWorkMatrix(const ScopedOriginalRobotWorkMatrix&)=delete;
    ScopedOriginalRobotWorkMatrix& operator=(const ScopedOriginalRobotWorkMatrix&)=delete;
    bool Active()const noexcept{return target_!=nullptr;}
};
}