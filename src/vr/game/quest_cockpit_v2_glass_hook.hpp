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
// PC original material_408c80 sets shader mode through bits 19..22;
// mode 4 = normal cubemap, mode 5 = environment reflection texture.
// Original 408F90 separately enables SPECULAR on bit 0.
// Only call after player+glass ownership is independently proven.
inline constexpr std::uint32_t RemoveGlassReflectionFlags(
    std::uint32_t flags) noexcept {
    const auto mode=(flags>>19)&15u;
    flags &= ~std::uint32_t{1}; // D3DRS_SPECULARENABLE OFF
    if(mode==4u||mode==5u)
        flags &= ~(std::uint32_t{15}<<19); // no reflection fixed shader
    return flags; // preserve all other render state / blend / depth flags
}
// Original 409430 layer env reflection modes: 0x02, 0x08, 0x80.
// Keep normal diffuse texture and filters; never touch world materials.
inline constexpr std::uint32_t RemoveGlassReflectionLayer(
    std::uint32_t flags) noexcept {
    return flags & ~std::uint32_t{0x8au};
}
inline void SuppressGlassReflectionColours(float* record18,
    bool removeGlass) noexcept {
    if(!record18)return;
    if(removeGlass) {
        for(unsigned i=0;i<16;++i)record18[i]=0.f;
        // Original 410DD0 computes combiner alpha from record[17].
        record18[17]=-1.f;
    } else {
        // Specular and emissive channels are distinct from diffuse tint.
        for(unsigned i=8;i<16;++i)record18[i]=0.f;
    }
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
