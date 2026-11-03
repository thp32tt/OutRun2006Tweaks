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
