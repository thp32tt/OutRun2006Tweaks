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
// The original PC passenger work matrix is rebuilt as T * F0 * B0
// (race_robot_driver_matrix_488af0: push B0, pre-multiply F0, then
// pre-multiply the seat translation). Quest cockpit vehicle rendering
// neutralizes F0 for the car itself. Remove that exact F0 contribution from
// an already-authored passenger W without replacing its seat/animation T.
//
// W' = W * inverse(F0 * B0) * B0
// For W = T * F0 * B0 this reduces exactly to T * B0.
// This is intentionally NOT the Quest W*C reflection correction, which is a
// separate native occupant transform and was proven unsafe as a substitute
// for the Windows passenger's pre-authored work matrix.
inline bool MultiplyAffineMatrices(const Matrix& left,const Matrix& right,
                                   Matrix& output) noexcept {
    if(!FiniteAffine(left)||!FiniteAffine(right))return false;
    Matrix candidate{};
    for(std::size_t row=0;row<4;++row) {
        for(std::size_t col=0;col<4;++col) {
            double acc=0.;
            for(std::size_t k=0;k<4;++k)
                acc+=double(left[row*4+k])*double(right[k*4+col]);
            candidate[row*4+col]=static_cast<float>(acc);
        }
    }
    if(!FiniteAffine(candidate))return false;
    output=candidate;
    return true;
}
inline bool InvertAffineMatrix(const Matrix& input,Matrix& output) noexcept {
    if(!FiniteAffine(input))return false;
    const double a=input[0], b=input[1], c=input[2];
    const double d=input[4], e=input[5], f=input[6];
    const double g=input[8], h=input[9], i=input[10];
    const double det=a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);
    if(!std::isfinite(det)||std::fabs(det)<=1.e-12)return false;
    const double invDet=1.0/det;
    Matrix inv=Identity;
    inv[0]=static_cast<float>((e*i-f*h)*invDet);
    inv[1]=static_cast<float>((c*h-b*i)*invDet);
    inv[2]=static_cast<float>((b*f-c*e)*invDet);
    inv[4]=static_cast<float>((f*g-d*i)*invDet);
    inv[5]=static_cast<float>((a*i-c*g)*invDet);
    inv[6]=static_cast<float>((c*d-a*f)*invDet);
    inv[8]=static_cast<float>((d*h-e*g)*invDet);
    inv[9]=static_cast<float>((b*g-a*h)*invDet);
    inv[10]=static_cast<float>((a*e-b*d)*invDet);
    for(std::size_t col=0;col<3;++col)
        inv[12+col]=-(input[12]*inv[col]+
                      input[13]*inv[4+col]+
                      input[14]*inv[8+col]);
    if(!FiniteAffine(inv))return false;
    output=inv;
    return true;
}
inline bool NeutralizePassengerVehicleF0(
    const Matrix& work,const Matrix& matrixB0,const Matrix& matrixF0,
    Matrix& output) noexcept {
    if(!FiniteAffine(work)||!FiniteAffine(matrixB0)||
       !FiniteAffine(matrixF0))return false;
    Matrix f0b0{},inverseF0B0{},withoutVehicleLocal{},candidate{};
    if(!MultiplyAffineMatrices(matrixF0,matrixB0,f0b0) ||
       !InvertAffineMatrix(f0b0,inverseF0B0) ||
       !MultiplyAffineMatrices(work,inverseF0B0,withoutVehicleLocal) ||
       !MultiplyAffineMatrices(withoutVehicleLocal,matrixB0,candidate))
        return false;
    output=candidate;
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