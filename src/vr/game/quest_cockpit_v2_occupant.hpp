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
// The Quest original computes B0/F0 correction BEFORE temporarily staging
// vehicle F0=identity, and holds the original correction for the entire
// scoped renderer operation (rather than reading a now-mutated car F0).
// Mirror that ordering only inside the exact synchronous PC player callback.
// This thread-local scope is NOT an OpenXR frame/eye owner and cannot survive
// the original callback; a work pointer, native frame epoch and XR pose must
// ALL match before the original pre-staging matrices may be consumed.
struct ScopedPreF0SnapshotData {
    std::uintptr_t playerIdentity=0;
    std::uint64_t nativeFrame=0, xrPoseSequence=0;
    Matrix matrixB0{},matrixF0{},correction{};
};
inline thread_local const ScopedPreF0SnapshotData* ActivePreF0Snapshot=nullptr;
class ScopedPreF0Snapshot final {
    const ScopedPreF0SnapshotData* const previous_;
    bool admitted_;
public:
    ScopedPreF0Snapshot(const ScopedPreF0SnapshotData& snapshot,
                        bool admitted) noexcept
        :previous_(ActivePreF0Snapshot),
         admitted_(admitted && !previous_ &&
                   snapshot.playerIdentity!=0 && snapshot.nativeFrame!=0 &&
                   snapshot.xrPoseSequence!=0 &&
                   FiniteAffine(snapshot.matrixB0) &&
                   FiniteAffine(snapshot.matrixF0) &&
                   FiniteAffine(snapshot.correction)) {
        if(admitted_)ActivePreF0Snapshot=&snapshot;
    }
    ~ScopedPreF0Snapshot() noexcept {
        if(admitted_)ActivePreF0Snapshot=previous_;
    }
    ScopedPreF0Snapshot(const ScopedPreF0Snapshot&)=delete;
    ScopedPreF0Snapshot& operator=(const ScopedPreF0Snapshot&)=delete;
    bool Active() const noexcept {return admitted_;}
};
inline const ScopedPreF0SnapshotData* MatchOriginalPreF0(
    std::uintptr_t playerIdentity,std::uint64_t nativeFrame,
    std::uint64_t xrPoseSequence) noexcept {
    const auto* s=ActivePreF0Snapshot;
    return s && s->playerIdentity==playerIdentity &&
        s->nativeFrame==nativeFrame && s->xrPoseSequence==xrPoseSequence
        ?s:nullptr;
}

// Quest original native callback at ELF 0x2E32B4/0x2E3374 admits
// event_state.slots[362].work_token OR slots[363].work_token.
// PC original event 362 ROB01 = driver, 363 ROB02 = conditional passenger.
// Both events dispatch the original 0x4879B0 display callback. Never infer
// identity from equal driver/heroine character tables or zero work IDs.
enum class OriginalOccupantSlot : std::uint16_t {
    None=0, Driver362=362, Passenger363=363
};
// HMD trace confirmed original ROB01/362 and ROB02/363 player tokens in
// the same render frame. Suppression is ONLY the driver's visual draw;
// GOAL, NPCs, and the passenger preserve native display calls.
enum class CockpitOccupantRender : std::uint8_t {
    Original=0, SuppressDriver=1, OriginalPassengerForceVisible=2
};
inline CockpitOccupantRender SelectCockpitOccupantRender(
    OriginalOccupantSlot slot,bool modeOne,bool racing,
    bool hideDriver,bool keepPassenger) noexcept
{
    if(!modeOne||!racing)return CockpitOccupantRender::Original;
    if(slot==OriginalOccupantSlot::Driver362&&hideDriver)
        return CockpitOccupantRender::SuppressDriver;
    if(slot==OriginalOccupantSlot::Passenger363&&keepPassenger)
        return CockpitOccupantRender::OriginalPassengerForceVisible;
    return CockpitOccupantRender::Original;
}
inline OriginalOccupantSlot ResolveOriginalCockpitWork(
    std::uintptr_t currentWork, std::uintptr_t driverWork,
    bool driverOriginalDisplay, std::uintptr_t passengerWork,
    bool passengerOriginalDisplay) noexcept {
    if(currentWork==0)return OriginalOccupantSlot::None;
    const bool driver=driverOriginalDisplay && driverWork!=0 &&
        currentWork==driverWork;
    const bool passenger=passengerOriginalDisplay && passengerWork!=0 &&
        currentWork==passengerWork;
    if(driver==passenger)return OriginalOccupantSlot::None;
    return driver?OriginalOccupantSlot::Driver362:
        OriginalOccupantSlot::Passenger363;
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
// Recursion in the original PC robot display may revisit this hook while
// the first draw has borrowed work+0x10. Never multiply W*C twice or let
// nested work writes defeat the outer RAII restore.
inline thread_local bool OriginalRobotCorrectionInFlight=false;
inline bool OriginalRobotCorrectionActive() noexcept {
    return OriginalRobotCorrectionInFlight;
}
class ScopedOriginalRobotCorrectionOwner final {
    bool active_=false;
public:
    explicit ScopedOriginalRobotCorrectionOwner(bool admitted) noexcept
        :active_(admitted && !OriginalRobotCorrectionInFlight) {
        if(active_)OriginalRobotCorrectionInFlight=true;
    }
    ~ScopedOriginalRobotCorrectionOwner() noexcept {
        if(active_)OriginalRobotCorrectionInFlight=false;
    }
    ScopedOriginalRobotCorrectionOwner(
        const ScopedOriginalRobotCorrectionOwner&)=delete;
    ScopedOriginalRobotCorrectionOwner& operator=(
        const ScopedOriginalRobotCorrectionOwner&)=delete;
    bool Active() const noexcept {return active_;}
};
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