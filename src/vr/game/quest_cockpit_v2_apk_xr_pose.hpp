// Source-parity translation of original Quest XrRig::locate at ARM64
// 0x2D69C8..0x2D6C08. Recenter yaw comes from xrLocateSpace; each
// xrLocateViews eye is composed with inverse(yawOrigin).
// This function does NOT re-add the Quest captured-profile +0.32Y/+0.55Z,
// nor the additional +0.04 angular term in run_game::$_2's later view-matrix
// branch. Original ELF re-disassembly proves those two mirrored branches are
// gated by VirtualWheel state bytes +0/+1 after VirtualWheel::update; they are
// virtual-hand wheel corrections, not a generic physical-wheel cockpit pose
// transform and not an extra translation on every tracked OpenXR eye.
// No XR handles, game memory writes, or allocations; pure C++17.
#pragma once
#include "quest_cockpit_v2_seat.hpp"
#include <array>
#include <cmath>
#include <limits>
namespace OutRunVR::QuestCockpitV2 {
struct NativeQuat {float x=0.f,y=0.f,z=0.f,w=1.f;};
struct NativePose {NativeQuat q{};Vec3 p{};};
inline bool NormalizeNativeQuat(NativeQuat in, NativeQuat& out) noexcept {
    if(!std::isfinite(in.x)||!std::isfinite(in.y)||
       !std::isfinite(in.z)||!std::isfinite(in.w))return false;
    const double norm=double(in.x)*in.x+double(in.y)*in.y+
                      double(in.z)*in.z+double(in.w)*in.w;
    if(!std::isfinite(norm)||norm<0.5||norm>1.5)return false;
    const double scale=1.0/std::sqrt(norm);
    const NativeQuat v{float(in.x*scale),float(in.y*scale),
                       float(in.z*scale),float(in.w*scale)};
    if(!std::isfinite(v.x)||!std::isfinite(v.y)||
       !std::isfinite(v.z)||!std::isfinite(v.w))return false;
    out=v;return true;
}
inline NativeQuat ConjugateNative(NativeQuat q) noexcept {
    return {-q.x,-q.y,-q.z,q.w};
}
inline NativeQuat ProductNative(NativeQuat a,NativeQuat b) noexcept {
    return {a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,
            a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,
            a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,
            a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z};
}
inline Vec3 RotateNative(NativeQuat q,Vec3 p) noexcept {
    const NativeQuat r=ProductNative(
        ProductNative(q,{p.x,p.y,p.z,0.f}),ConjugateNative(q));
    return {r.x,r.y,r.z};
}
inline bool NativeYawOrigin(NativePose head, NativePose& origin) noexcept {
    NativeQuat q{};
    if(!Finite(head.p)||!NormalizeNativeQuat(head.q,q))return false;
    // 2D6A60..2D6A90: atan2(2*(qx*qz+qy*qw),
    //                      1-2*(qx*qx+qy*qy)).
    // 2D6A94..2D6AD0: yaw-only quaternion (0,sin(yaw/2),0,cos(yaw/2))
    // and same xrLocateSpace position, captured once on recenter.
    const float num=2.f*(q.x*q.z+q.y*q.w);
    const float denom=1.f-2.f*(q.x*q.x+q.y*q.y);
    const float half=0.5f*std::atan2(num,denom);
    NativePose candidate{};
    candidate.q={0.f,std::sin(half),0.f,std::cos(half)};
    candidate.p=head.p;
    if(!Finite(candidate.p)||!std::isfinite(candidate.q.y)||
       !std::isfinite(candidate.q.w))return false;
    origin=candidate;
    return true;
}
inline bool NativeInverseOriginCompose(NativePose origin,NativePose pose,
                                       NativePose& out) noexcept {
    NativeQuat o{},p{};
    if(!Finite(origin.p)||!Finite(pose.p)||
       !NormalizeNativeQuat(origin.q,o)||
       !NormalizeNativeQuat(pose.q,p))return false;
    const NativeQuat inv=ConjugateNative(o);
    NativeQuat result{};
    if(!NormalizeNativeQuat(ProductNative(inv,p),result))return false;
    const Vec3 delta{pose.p.x-origin.p.x,pose.p.y-origin.p.y,
                     pose.p.z-origin.p.z};
    const Vec3 relative=RotateNative(inv,delta);
    if(!Finite(relative))return false;
    out={result,relative};
    return true;
}
inline bool NativeHeadLocalEye(NativePose head,NativePose localEye,
                               NativePose& out) noexcept {
    NativeQuat h{},e{},q{};
    if(!Finite(head.p)||!Finite(localEye.p)||
       !NormalizeNativeQuat(head.q,h)||
       !NormalizeNativeQuat(localEye.q,e)||
       !NormalizeNativeQuat(ProductNative(h,e),q))return false;
    const Vec3 local=RotateNative(h,localEye.p);
    const Vec3 position{head.p.x+local.x,head.p.y+local.y,
                        head.p.z+local.z};
    if(!Finite(position))return false;
    out={q,position};return true;
}
// Native 2D6B98..2D6BFC, both eyes: inverse(xrLocateSpace yawOrigin)
// composed with each unmodified xrLocateViews eye pose.
inline bool NativeStereoEye(NativePose yawOrigin,NativePose head,
    NativePose localEye,NativePose& relativeEye) noexcept {
    NativePose world{};
    return NativeHeadLocalEye(head,localEye,world) &&
           NativeInverseOriginCompose(yawOrigin,world,relativeEye);
}
}
