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

// Apply the DIFFERENCE between Quest's 30-profile seat and native view1
// anchor, not the absolute profile and not a second vehicle B0 transform.
// The original PC CalcCameraMatrix has ALREADY converted the view1 anchor
// through its car/swing/blend pipeline. Its horizontal smoothed direction is
// the translation basis, avoiding per-frame raw-B0 jitter in the user's test.
// Local right is (+Z,0,-X) around the game camera forward; Y stays world-up.
// Quest run_game separately adds (+0.32,+0.55) to the captured Y/Z and the
// XR view construction cancels this with (-0.32,-0.55) in a rotated basis;
// NEVER add those unpaired constants again to this existing PC OpenXR view.
inline bool NativeVrProfilePose(
    Vec3 nativeEye, Vec3 nativeLook, Vec3 originalAnchor,
    Vec3 questProfile, float extraBack, float extraDown, float extraRight,
    SeatPose& output) noexcept {
    if (!Finite(nativeEye)||!Finite(nativeLook)||
        !Finite(originalAnchor)||!Finite(questProfile)||
        !std::isfinite(extraBack)||!std::isfinite(extraDown)||
        !std::isfinite(extraRight)||
        extraBack<0.f||extraBack>1.2f||
        extraDown<0.f||extraDown>0.8f||
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
       back<0.f||back>1.2f||down<0.f||down>0.8f||
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
