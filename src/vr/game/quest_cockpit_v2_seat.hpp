// QuestCockpitV2 native per-model mode-1 camera anchor.
// Canonical PC/Quest have 30 records of 36 bytes but 15 distinct XYZ anchors:
// car i and i+15 share the FIRST THREE local-space coordinates.
// Do not invent a constant seat offset or reinterpret OpenXR metres.
#pragma once
#include "quest_cockpit_v2_runtime.hpp"
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace OutRunVR::QuestCockpitV2 {
struct Vec3 {float x=0.f,y=0.f,z=0.f;};
struct SeatPose {Vec3 eye{},look{};std::uint8_t model=0;};
inline bool Finite(Vec3 v) noexcept {
    return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z);
}
// The original PC mode1 table is copied into mutable game RAM during
// initialization. The native cockpit hook may install before that copy.
// Accept an initial snapshot only when all 30 live XYZ anchors equal the
// verified original PE source; otherwise restoring a premature zero table
// can corrupt the camera after START/GOAL or an F11 toggle.
// The remaining 24 bytes of each record are not VR-seat inputs and are
// deliberately left to the original game.
inline bool OriginalModeOneTableInitialized(
    const std::uint8_t* live, std::size_t liveBytes,
    const std::uint8_t* original, std::size_t originalBytes) noexcept {
    constexpr std::size_t kStride=36u,kCount=30u,kXYZ=3u*sizeof(float);
    if(!live || !original || liveBytes<kStride*kCount ||
       originalBytes<kStride*kCount) return false;
    for(std::size_t i=0;i<kCount;++i) {
        Vec3 expected{},actual{};
        std::memcpy(&expected,original+i*kStride,kXYZ);
        std::memcpy(&actual,live+i*kStride,kXYZ);
        if(!Finite(expected) || !Finite(actual) ||
           std::fabs(expected.x)>5.f || std::fabs(expected.y)>5.f ||
           std::fabs(expected.z)>5.f ||
           std::memcmp(&actual,&expected,kXYZ)!=0) return false;
    }
    return true;
}

inline bool OriginalModeOneAnchor(
    const std::uint8_t* verifiedTable, std::size_t tableBytes,
    int carModel, Vec3& destination) noexcept {
    constexpr std::size_t kStride=36u,kCount=30u;
    if(!verifiedTable || tableBytes<kStride*kCount ||
       carModel<0 || carModel>=static_cast<int>(kCount))return false;
    Vec3 local{};
    static_assert(sizeof(local)==12u);
    std::memcpy(&local,verifiedTable+static_cast<std::size_t>(carModel)*kStride,
                sizeof(local));
    if(!Finite(local) || std::fabs(local.x)>5.f ||
       std::fabs(local.y)>5.f || std::fabs(local.z)>5.f)return false;
    destination=local;
    return true;
}

// Quest native run_game::$_2 reads a second ORIGINAL guest-profile table,
// not the 30x36 original mode1 camera anchors. Each car has its OWN 0x128
// record. The original PE table of 30 addresses begins at guest VA 5B2F68;
// the first record is guest VA 5B0CB8. No original game assets are bundled.
// Reject an unknown executable rather than guessing a seat or indexing blindly.
inline bool OriginalQuestVrProfileAnchor(
    const std::uint8_t* guestPointers, std::size_t pointerBytes,
    const std::uint8_t* guestRecords, std::size_t recordBytes,
    int carModel, Vec3& destination) noexcept {
    constexpr std::size_t kCount=30u, kStride=0x128u, kXYZ=0x4cu;
    constexpr std::uint32_t kFirstVA=0x005b0cb8u;
    constexpr std::uint32_t kPtrVA=0x005b2f68u;
    static_assert(kFirstVA+kCount*kStride==kPtrVA);
    if (!guestPointers || !guestRecords || carModel<0 ||
        carModel>=static_cast<int>(kCount) ||
        pointerBytes<kCount*sizeof(std::uint32_t) ||
        recordBytes<kCount*kStride) return false;
    const auto i=static_cast<std::size_t>(carModel);
    std::uint32_t pointer=0;
    std::memcpy(&pointer,guestPointers+i*sizeof(pointer),sizeof(pointer));
    if (pointer!=kFirstVA+static_cast<std::uint32_t>(i*kStride))return false;
    Vec3 candidate{};
    std::memcpy(&candidate,guestRecords+i*kStride+kXYZ,sizeof(candidate));
    if (!Finite(candidate) || std::fabs(candidate.x)>5.f ||
        std::fabs(candidate.y)>5.f || std::fabs(candidate.z)>5.f)return false;
    destination=candidate;
    return true;
}

// Original APK ARM64 verified chained data flow on 2026-11-05:
//   0x2E14E8 loads x12=[closure+64], guest profile output buffer.
//   0x2E1598 writes selected guest X to [x12].
//   0x2E1650 writes guest Y to [x12+4].
//   0x2E16C4 writes guest Z to [x12+8].
//   0x2E17F4..0x2E1808 reads Y/Z from this SAME captured output
//   buffer, adds original ELF rodata pair (+0.32,+0.55) and stores it.
//   Later 0x2E1B00..0x2E1D18 also references this vector, but its two
//   branches are gated by bytes owned by outrun::quest::VirtualWheel::update;
//   they are NOT an unconditional HMD seat-height cancellation.
// This is original per-car camera input data, NOT a generic world
// HMD translation. Never add or subtract the pair again from every OpenXR eye.
// Quest run_game::$_5 at 0x2E3690..0x2E36C8 enables
// PcRaceCameraInputs only when guest state==0x10 (STATE_GAME) and the captured
// PadSnapshot toggle is asserted. 2026-11-10 exact closure reconstruction
// closes that former gap: run_game::$_2 closure+0x20 is the same sp+0x48 byte
// captured by $_5. $_2 asserts it only after profile XYZ lookup succeeds and
// finally ANDs it with 0.05 < virtual-wheel radius < 0.4 at 0x2E17B0..0x2E1804.
// run_game::$_3's original debug string proves sp+0x64 is "radius" and sp+0x60
// is "tilt"; android_main initializes radius to 0.175 at 0x2DBA5C..0x2DBA6C.
// Thus a valid default Quest profile naturally asserts this gate even without
// synthesizing any physical-wheel camera-yaw rule on Windows.
inline constexpr float OriginalQuestDefaultVirtualWheelRadius=0.175f;
inline bool OriginalQuestPadSnapshotCameraInputValid(
    bool profileValid,float virtualWheelRadius) noexcept {
    return profileValid && std::isfinite(virtualWheelRadius) &&
           virtualWheelRadius>0.05f && virtualWheelRadius<0.4f;
}
inline bool OriginalQuestGameCameraState(std::uint32_t guestState) noexcept {
    return guestState==0x10u;
}
inline bool OriginalQuestModeOneInput(Vec3 guestProfile,
                                      Vec3& destination) noexcept {
    if(!Finite(guestProfile) || std::fabs(guestProfile.x)>5.f ||
       std::fabs(guestProfile.y)>5.f ||
       std::fabs(guestProfile.z)>5.f) return false;
    const Vec3 next{guestProfile.x,guestProfile.y+0.319999993f,
                    guestProfile.z+0.550000012f};
    if(!Finite(next) || std::fabs(next.y)>5.f ||
       std::fabs(next.z)>5.f) return false;
    destination=next;return true;
}
// The native guest output buffer receives the car-profile values first;
// retaining this source-order guard prevents a mistaken double transform.
// HMD feedback: positive mode1 local Z moves eye rearward; positive
// SeatDown moves it downward. Both offsets are now signed in F11.
// Runtime-safe PC bridge: substitute the Quest profile as the ORIGINAL
// mode-1 camera input before race_camera_eye_look_485590 performs eye swing,
// view blend/snap and the ground-height clamp. This is the phase used by the
// Quest native path. Never apply this value as a post-camera world delta.
inline bool NativeVrProfileInputAnchor(
    Vec3 questProfile, float extraBack, float extraDown, float extraRight,
    Vec3& destination) noexcept {
    if (!Finite(questProfile) || !std::isfinite(extraBack) ||
        !std::isfinite(extraDown) || !std::isfinite(extraRight) ||
        std::fabs(extraBack) > 1.2f ||
        extraDown < -1.0f || extraDown > 0.8f ||
        std::fabs(extraRight) > 0.6f)
        return false;
    const Vec3 candidate{
        questProfile.x + extraRight,
        questProfile.y - extraDown,
        questProfile.z + extraBack
    };
    if (!Finite(candidate) || std::fabs(candidate.x) > 5.f ||
        std::fabs(candidate.y) > 5.f || std::fabs(candidate.z) > 5.f)
        return false;
    destination = candidate;
    return true;
}

// HMD-rejected legacy approximation retained only as a pure comparison helper.
// Runtime no longer applies this after the original camera has been completed.
// Apply the DIFFERENCE between Quest's 30-profile seat and native view1
// anchor, not the absolute profile and not a second vehicle B0 transform.
// The original PC CalcCameraMatrix has ALREADY converted the view1 anchor
// through its car/swing/blend pipeline. Its horizontal smoothed direction is
// the translation basis, avoiding per-frame raw-B0 jitter in the user's test.
// Local right is (+Z,0,-X) around the game camera forward; Y stays world-up.
// Quest run_game separately adds (+0.32,+0.55) to the captured Y/Z.
// The later (-0.32,-0.55) arithmetic is VirtualWheel-state conditional,
// not a universal XR seat cancellation; NEVER synthesize it as a fixed
// post-camera offset in this legacy comparison helper.
inline bool NativeVrProfilePose(
    Vec3 nativeEye, Vec3 nativeLook, Vec3 originalAnchor,
    Vec3 questProfile, float extraBack, float extraDown, float extraRight,
    SeatPose& output) noexcept {
    if (!Finite(nativeEye)||!Finite(nativeLook)||
        !Finite(originalAnchor)||!Finite(questProfile)||
        !std::isfinite(extraBack)||!std::isfinite(extraDown)||
        !std::isfinite(extraRight)||
        std::fabs(extraBack)>1.2f||
        extraDown< -1.0f||extraDown>0.8f||
        std::fabs(extraRight)>0.6f)return false;
    const double dx=double(nativeLook.x)-nativeEye.x;
    const double dz=double(nativeLook.z)-nativeEye.z;
    const double n=std::hypot(dx,dz);
    if(!std::isfinite(n)||n<1.e-5)return false;
    const double forward=double(questProfile.z)-originalAnchor.z-extraBack;
    const double right=double(questProfile.x)-originalAnchor.x+extraRight;
    const double up=double(questProfile.y)-originalAnchor.y-extraDown;
    if (std::fabs(forward)>5. || std::fabs(right)>5. || std::fabs(up)>5.)
        return false;
    const double fx=dx/n,fz=dz/n;
    const Vec3 delta{static_cast<float>(fx*forward+fz*right),
                     static_cast<float>(up),
                     static_cast<float>(fz*forward-fx*right)};
    const Vec3 newEye{
        float(double(nativeEye.x)+delta.x),
        float(double(nativeEye.y)+delta.y),
        float(double(nativeEye.z)+delta.z)};
    const Vec3 newLook{
        float(double(nativeLook.x)+delta.x),
        float(double(nativeLook.y)+delta.y),
        float(double(nativeLook.z)+delta.z)};
    if (!Finite(newEye)||!Finite(newLook))return false;
    SeatPose candidate{};candidate.eye=newEye;candidate.look=newLook;
    output=candidate;
    return true;
}
// EXPERIMENTAL B0 camera-only A/B. Never the normal QuestCockpitV2 path:
// the original native mode1 camera calculates the seat from this table.
// The game's row-vector D3D car basis transforms an original game-unit seat
// point exactly once. HMD-relative 6DoF is applied later by the existing
// OpenXR stereo renderer, never multiplied into this owner twice.
inline bool SeatPoseFromCar(const Matrix& carB0,Vec3 local,
                           SeatPose& destination) noexcept {
    if(!FiniteAffine(carB0) || !Finite(local))return false;
    auto axis=[&](std::size_t column) noexcept {
        return Vec3{
            carB0[column]*local.x+carB0[4+column]*local.y+
                carB0[8+column]*local.z+carB0[12+column],
            0.f,0.f};
    };
    const Vec3 px=axis(0),py=axis(1),pz=axis(2);
    Vec3 eye{px.x,py.x,pz.x};
    // +row 3 is the existing original game player-car forward convention.
    const Vec3 f{carB0[8],carB0[9],carB0[10]};
    const double length=std::sqrt(double(f.x)*f.x+
                                    double(f.y)*f.y+double(f.z)*f.z);
    if(!std::isfinite(length)||length<1.0e-5||length>100.)return false;
    const Vec3 look{float(double(eye.x)+f.x/length),
                    float(double(eye.y)+f.y/length),
                    float(double(eye.z)+f.z/length)};
    if(!Finite(eye)||!Finite(look))return false;
    SeatPose tmp{};
    tmp.eye=eye;tmp.look=look;
    destination=tmp;
    return true;
}
// Apply an additive POST-original-camera offset, NEVER a second raw B0
// transform of the model's 30x36 mode1 seat anchor. Keep original swing,
// blend and view direction. Camera offset is in native game coordinates.
inline bool NativeSeatOffset(Vec3 eye,Vec3 look,float back,float down,
                             float right,SeatPose& output) noexcept {
    if(!Finite(eye)||!Finite(look)||!std::isfinite(back)||
       !std::isfinite(down)||!std::isfinite(right)||
       std::fabs(back)>1.2f||down< -1.0f||down>0.8f||
       std::fabs(right)>0.6f)return false;
    const double dx=double(look.x)-eye.x,dz=double(look.z)-eye.z;
    const double norm=std::hypot(dx,dz);
    if(!std::isfinite(norm)||norm<1.e-5)return false;
    const float fx=static_cast<float>(dx/norm),fz=static_cast<float>(dz/norm);
    const Vec3 shift{-fx*back+fz*right,-down,-fz*back-fx*right};
    SeatPose candidate{};
    candidate.eye={eye.x+shift.x,eye.y+shift.y,eye.z+shift.z};
    candidate.look={look.x+shift.x,look.y+shift.y,look.z+shift.z};
    if(!Finite(candidate.eye)||!Finite(candidate.look))return false;
    output=candidate;return true;
}
// Deterministic, game-frame-only owner gate (no old camera offset/session
// caching): native view1, gameplay, original verified player, and world pass.
inline bool TrialEligible(bool requested,bool vrEnabled,bool gameplay,
                          std::uint8_t nativeMode,bool sceneEffect,
                          bool playerValid) noexcept {
    return requested && vrEnabled && gameplay && nativeMode==1 &&
           !sceneEffect && playerValid;
}
}
