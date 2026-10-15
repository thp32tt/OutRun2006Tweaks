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
    constexpr int RetailPeriodicMagnitudeScale = 50;
    constexpr int RetailPeriodicStartThreshold = 27;
    constexpr float RetailSurfaceRoughnessMax = 0.90f;
    constexpr float RetailSurfaceBoost = 1.25f;
    constexpr float RetailSurfaceEnvelopeMax =
        RetailSurfaceRoughnessMax * RetailSurfaceBoost;

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

    // The retail periodic source path at 0x00132E94 multiplies the
    // four-wheel surface envelope by min(field_1C4, 1.0) before handing it to
    // the FFB manager. Keep this factor separate from drive_factor(): retail
    // applies both.
    inline float surface_speed_factor(float speedRaw)
    {
        if (!std::isfinite(speedRaw))
            return 0.0f;
        return std::clamp(speedRaw, 0.0f, 1.0f);
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

    // Retail wheel-specific feedback level:
    //   - the options control is 0..10;
    //   - wheel-device mode stores it in game-state byte +0xFC;
    //   - invalid values >= 11 are reset to 0;
    //   - level 0 disables the surface-feedback producer;
    //   - the Type-4 manager uses (level + 1) / 11 for non-zero levels.
    //
    // The exact localized retail menu label is still unresolved, so keep the
    // semantic name deliberately generic. PC Road Detail remains a separate
    // host/user scaler; Road Detail 1.00 corresponds to retail level 10's
    // multiplier of 1.0, without inventing the retail default level.
    inline float retail_wheel_level_scale(int level)
    {
        if (level < 1 || level > 10)
            return 0.0f;
        return static_cast<float>(level + 1) / 11.0f;
    }

    // The retail surface producer writes max four-wheel roughness first, then
    // overwrites the Type-4 source with roughness*1.25 when roughness > 0.30
    // and either of the recovered car-field predicates is true:
    //   field_268 < 0.10
    //   otherwise field_264 > -0.10
    // Keep the field names numeric until their gameplay semantics are proven.
    inline float surface_envelope(
        float roughness,
        float carField264,
        float carField268)
    {
        if (!std::isfinite(roughness))
            return 0.0f;
        roughness = std::clamp(
            roughness, 0.0f, RetailSurfaceRoughnessMax);

        if (roughness <= 0.30f)
            return roughness;

        const bool firstPredicate =
            std::isfinite(carField268) && carField268 < 0.10f;
        const bool secondPredicate =
            !firstPredicate &&
            std::isfinite(carField264) && carField264 > -0.10f;
        return (firstPredicate || secondPredicate)
            ? roughness * RetailSurfaceBoost
            : roughness;
    }

    // Retail steady-state Type-4 magnitude chain:
    //   0x001D7C88: resolve each wheel surface mask
    //   0x001D80A8..0x001D810C: retain the maximum envelope
    //   0x00132E94..0x00132EA0: multiply by min(field_1C4, 1.0)
    //   0x001332BC..0x00133340: apply wheel level (level + 1) / 11
    //   0x00133328..0x0013334C: * driveFactor * 50, round,
    //                           and suppress values below raw 27.
    //
    // wheelLevelScale is explicit because the retail multiplier is now
    // identified as the wheel-specific 0..10 feedback-strength level, not a
    // transient activation/recreate ramp. The PC runtime passes 1.0 here and
    // keeps its independent DD-safe warm-up/recreate ramp downstream.
    inline int periodic_magnitude_raw(
        float surfaceEnvelope,
        float speedRaw,
        float factor,
        float wheelLevelScale = 1.0f)
    {
        surfaceEnvelope = std::isfinite(surfaceEnvelope)
            ? std::clamp(surfaceEnvelope, 0.0f, RetailSurfaceEnvelopeMax)
            : 0.0f;
        factor = std::isfinite(factor)
            ? std::clamp(factor, 0.0f, 1.0f) : 0.0f;
        wheelLevelScale = std::isfinite(wheelLevelScale)
            ? std::clamp(wheelLevelScale, 0.0f, 1.0f) : 0.0f;
        const float raw =
            surfaceEnvelope * surface_speed_factor(speedRaw) *
            factor * static_cast<float>(RetailPeriodicMagnitudeScale) *
            wheelLevelScale;
        return std::clamp(
            static_cast<int>(std::lround(raw)), 0, LogitechScaleMax);
    }

    inline float periodic_magnitude_norm(
        float surfaceEnvelope,
        float speedRaw,
        float factor,
        float wheelLevelScale = 1.0f)
    {
        const int raw = periodic_magnitude_raw(
            surfaceEnvelope, speedRaw, factor, wheelLevelScale);
        if (raw < RetailPeriodicStartThreshold)
            return 0.0f;
        return static_cast<float>(raw) /
            static_cast<float>(LogitechScaleMax);
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

    inline float triangle_wave(float phaseCycles)
    {
        if (!std::isfinite(phaseCycles))
            return 0.0f;
        phaseCycles = std::fmod(phaseCycles, 1.0f);
        if (phaseCycles < 0.0f)
            phaseCycles += 1.0f;
        // -1 at cycle 0, +1 at 0.5, back to -1 at cycle 1.
        return 1.0f - 4.0f * std::abs(phaseCycles - 0.5f);
    }
}
