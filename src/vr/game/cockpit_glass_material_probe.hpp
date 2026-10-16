#pragma once
#include <cstdint>
namespace OutRunVR::CockpitGlassProbe {
    // Quest candidate blends only; insufficient to prove a glass polygon.
    constexpr bool CandidateBlend(std::uint32_t attr) noexcept {
        auto src=(attr>>8)&15u, dst=(attr>>12)&15u;
        return (src==1u||src==4u)&&dst==5u;
    }
    static_assert(CandidateBlend(0x5100u));
    static_assert(CandidateBlend(0x5400u));
    static_assert(!CandidateBlend(0x5500u));
    static_assert(!CandidateBlend(0x1100u));
}
