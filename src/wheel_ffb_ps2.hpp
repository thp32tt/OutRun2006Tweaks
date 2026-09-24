#pragma once

#include <algorithm>
#include <cmath>

namespace WheelFFBPS2
{
    // Retail OutRun 2 SP PS2 evidence, SLPM_666.28:
    //   0x001354B0 condition download
    //   0x00135640 condition update
    //   0x001357B8 constant download
    //   0x00135910 constant update
    //   0x00135D40 periodic download
    //   0x00135EB0 periodic update
    //
    // The common Logitech lgdev descriptor is 0x3c bytes. The type IDs below
    // are corroborated by other contemporary liblgdev source/decomp material.
    // Only values also observed in OutRun's retail binary are exposed here as
    // retail constants. Cross-title tuning values are never imported.

    constexpr int LogitechScaleMax = 255;
    constexpr int TypeConstant = 0;
    constexpr int TypeTriangle = 4;
    constexpr int TypeSpring = 7;
    constexpr int TypeDamper = 8;

    constexpr int RetailInitialSpringSaturation = 70;
    constexpr int RetailInitialSpringCoefficient = 70;

    constexpr int RetailSpringSaturationBase = 15;
    constexpr int RetailSpringSaturationSpan = 45;
    constexpr int RetailSpringCoefficient = 200;

    constexpr int RetailDamperSaturation = 255;
    constexpr int RetailConstantMagnitudeCap = 220;

    constexpr int RetailPeriodicDirectionDegrees = 90;
    constexpr int RetailPeriodicPhase = 0;
    constexpr int RetailPeriodicOffset = 0;
    constexpr int RetailPeriodicBasePeriod = 100;
    constexpr int RetailPeriodicPeriodSpan = 60;

    // The retail game first stores min(field_1C4 / 2.5, 1.0), then its FFB
    // update divides that value by 0.35 and clamps again. Algebraically this is
    // clamp(field_1C4 / 0.875, 0, 1). Keep it separate from the Modern DD
    // field_1C4/2.0 speed normalization.
    inline float drive_factor(float speedRaw)
    {
        if (!std::isfinite(speedRaw))
            return 0.0f;
        return std::clamp(speedRaw / 0.875f, 0.0f, 1.0f);
    }

    inline int spring_saturation_raw(float factor)
    {
        factor = std::isfinite(factor) ? std::clamp(factor, 0.0f, 1.0f) : 0.0f;
        // MIPS cvt.w.s uses the active FP rounding mode. Round-to-nearest is the
        // normal game/runtime mode, so lround is the closest portable mapping.
        return std::clamp(
            RetailSpringSaturationBase +
                static_cast<int>(std::lround(RetailSpringSaturationSpan * factor)),
            0, LogitechScaleMax);
    }

    inline float spring_saturation_norm(float factor)
    {
        return static_cast<float>(spring_saturation_raw(factor)) /
            static_cast<float>(LogitechScaleMax);
    }

    inline float spring_coefficient_norm()
    {
        return static_cast<float>(RetailSpringCoefficient) /
            static_cast<float>(LogitechScaleMax);
    }

    inline float constant_magnitude_cap_norm()
    {
        return static_cast<float>(RetailConstantMagnitudeCap) /
            static_cast<float>(LogitechScaleMax);
    }

    inline int damper_coefficient_raw(float factor)
    {
        factor = std::isfinite(factor) ? std::clamp(factor, 0.0f, 1.0f) : 0.0f;
        return std::clamp(
            static_cast<int>(std::lround(10.0f * (1.0f - factor))),
            0, LogitechScaleMax);
    }

    inline float damper_coefficient_norm(float factor)
    {
        return static_cast<float>(damper_coefficient_raw(factor)) /
            static_cast<float>(LogitechScaleMax);
    }

    inline float damper_saturation_norm()
    {
        return static_cast<float>(RetailDamperSaturation) /
            static_cast<float>(LogitechScaleMax);
    }

    inline int triangle_period_raw(float factor)
    {
        factor = std::isfinite(factor) ? std::clamp(factor, 0.0f, 1.0f) : 0.0f;
        return RetailPeriodicBasePeriod +
            static_cast<int>(std::lround(RetailPeriodicPeriodSpan * factor));
    }

    // SLPM proves the raw period field is 100 + 60*driveFactor. liblgdev's
    // public ecosystem uses small period values such as 80 for wheel periodic
    // effects; for DirectInput translation we interpret the raw value as
    // milliseconds. This conversion is explicitly a host translation
    // assumption, not a claim that the retail binary stores Hertz.
    inline float triangle_frequency_hz_for_directinput(float factor)
    {
        const int period = std::max(1, triangle_period_raw(factor));
        return 1000.0f / static_cast<float>(period);
    }
}
