// Read-only game yaw word comparison. PC/Quest original function 483110.
#pragma once
#include <cstdint>
#include <cmath>
#include <limits>
namespace OutRunVR::QuestCockpitV2 {
inline float YawWordDeltaDegrees(std::uint16_t now,
                                 std::uint16_t before) noexcept {
    constexpr float k=360.f/65536.f;
    const std::uint16_t w=static_cast<std::uint16_t>(now-before);
    const std::int32_t d=w<=0x7fffu
        ? static_cast<std::int32_t>(w)
        : static_cast<std::int32_t>(w)-65536;
    return static_cast<float>(d)*k;
}
inline float YawRadiansStepDegrees(float now,float before) noexcept {
    if(!std::isfinite(now)||!std::isfinite(before))
        return std::numeric_limits<float>::quiet_NaN();
    constexpr float tau=6.2831853071795864769f;
    constexpr float radToDeg=57.295779513082320877f;
    return std::remainder(now-before,tau)*radToDeg;
}
}
