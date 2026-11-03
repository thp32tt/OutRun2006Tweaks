#pragma once
// Quest APK-derived selective PC player-glass material gate. PURE C++17.
// This checks only the exact dark-tint/alpha/blend family, not scene light.
// A material candidate is never, by itself, player glass ownership.
#include <cmath>
#include <cstdint>

namespace OutRunVR::QuestCockpitV2::Glass {
inline constexpr bool Blend(std::uint32_t flags,
    std::uint32_t srcEffective, std::uint32_t dstEffective) noexcept
{
    const auto src=(flags>>8)&15u, dst=(flags>>12)&15u;
    return ((src==1u&&srcEffective==2u) ||
            (src==4u&&srcEffective==5u)) &&
           dst==5u && dstEffective==6u;
}
inline bool GlassDiffuse(float r,float g,float b,float a) noexcept {
    if (!std::isfinite(r)||!std::isfinite(g)||
        !std::isfinite(b)||!std::isfinite(a))return false;
    const bool alpha=std::fabs(a-.55f)<.001f ||
                     std::fabs(a-.425f)<.001f;
    const float hi=r>g?(r>b?r:b):(g>b?g:b);
    const float lo=r<g?(r<b?r:b):(g<b?g:b);
    return alpha && r>=.10f && r<=.42f &&
           g>=.10f && g<=.42f && b>=.10f && b<=.42f &&
           hi-lo<.005f;
}
inline float AlphaFromBrightness(float percent) noexcept {
    if(!std::isfinite(percent))return .30f;
    if(percent<0.f)percent=0.f;
    if(percent>100.f)percent=100.f;
    return .90f-.008f*percent;
}
inline bool Admit(bool vr,bool cockpit,bool enabled,bool gameplay,
    bool nativeEpoch,bool mode1,bool notEffect,bool owner,bool alphaBlend,
    bool materialBlend,bool diffuse,bool uniqueColor) noexcept
{
    return vr&&cockpit&&enabled&&gameplay&&nativeEpoch&&mode1&&
        notEffect&&owner&&alphaBlend&&materialBlend&&diffuse&&uniqueColor;
}
static_assert(Blend(0x5100u,2u,6u));
static_assert(Blend(0x5400u,5u,6u));
static_assert(!Blend(0x5500u,5u,6u));
static_assert(!Blend(0x5100u,1u,6u));
}
