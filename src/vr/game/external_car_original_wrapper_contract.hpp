#pragma once
// EXT16-008: independently checked CALL edges in the canonical PE32 player
// display wrapper. A 49F3E0 trampoline is NOT a body-only raster leaf:
// CALL 46BD30 is followed by a second CALL 49A650 (bare RET in the
// decompiled canonical PC build). Most importantly, 46BD30 owns lighting,
// matrices and 469600 car rendering, including 422550/422740 shadow-volume
// leaves, NOT only exterior triangles. Reference:
// r4dius/outrun2-decomp@e1e1c592, src/platform/pc_vehicle_display.cpp
// and src/platform/vehicle_model_draw.cpp. The actual canonical PE32
// wrapper/RET bytes are checked by verify_original_player_callback_abi.py.
// Do not suppress either parent function as a "body-only" draw leaf.
#include <array>
#include <cstddef>
#include <cstdint>

namespace OutRunVR::DinoSidecar {
inline constexpr std::uint32_t RetailPlayerWrapperVa=0x0049F3E0u;
inline constexpr std::uint32_t RetailPlayerDisplayCallVa=0x0046BD30u;
inline constexpr std::uint32_t RetailPlayerFollowupCallVa=0x0049A650u;
inline constexpr std::array<std::uint8_t,24> RetailPlayerWrapperPrefix{{
    0x56,0x8B,0x74,0x24,0x08,0x56,0xE8,0x45,
    0xC9,0xFC,0xFF,0x68,0xF0,0xE7,0x82,0x00,
    0x56,0xE8,0x5A,0xB2,0xFF,0xFF,0x83,0xC4
}};

// The unsigned wrap computes near rel32 targets identically on x86 and the
// Linux regression runner, including negative two's-complement displacements.
constexpr std::uint32_t RetailCallTarget(const std::uint8_t* p,
    std::size_t len,std::size_t callOffset,
    std::uint32_t functionVa=RetailPlayerWrapperVa) noexcept {
    if(!p || callOffset+5u>len || p[callOffset]!=0xE8u)return 0u;
    const std::uint32_t disp=std::uint32_t(p[callOffset+1]) |
        (std::uint32_t(p[callOffset+2])<<8u) |
        (std::uint32_t(p[callOffset+3])<<16u) |
        (std::uint32_t(p[callOffset+4])<<24u);
    return functionVa+static_cast<std::uint32_t>(callOffset)+5u+disp;
}
constexpr bool ExactRetailPlayerWrapperTwoCalls(const std::uint8_t* p,
    std::size_t len) noexcept {
    if(!p || len<RetailPlayerWrapperPrefix.size())return false;
    for(std::size_t i=0;i<RetailPlayerWrapperPrefix.size();++i)
        if(p[i]!=RetailPlayerWrapperPrefix[i])return false;
    return RetailCallTarget(p,len,6u)==RetailPlayerDisplayCallVa &&
        RetailCallTarget(p,len,17u)==RetailPlayerFollowupCallVa;
}
static_assert(ExactRetailPlayerWrapperTwoCalls(
    RetailPlayerWrapperPrefix.data(),RetailPlayerWrapperPrefix.size()),
    "Retail player wrapper CALL targets changed");

// NOTE: even proving the wrapper signature does NOT prove an isolated BODY
// draw leaf; 46BD30 could own stock gauges/glass/shadow/ancillary draws.
// The complete wrapper (including 49A650) is unconditionally preserved.
// Future external rendering must target an independently proven inner
// body-only leaf AFTER isolated two-eye staging, never flip this function.
inline constexpr bool MaySkipRetailPlayerWrapper() noexcept {return false;}
} // namespace OutRunVR::DinoSidecar
