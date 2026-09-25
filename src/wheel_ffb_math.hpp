#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <string>
#include <string_view>

namespace WheelFFBMath
{
    enum class Model : int
    {
        ModernDD = 0,
        ArcadeOriginal = 1,
        ArcadeHybrid = 2,
        PS2OriginalExperimental = 3,
    };

    inline Model sanitize_model(int value)
    {
        return static_cast<Model>(std::clamp(value, 0, 3));
    }

    inline const char* model_name(Model model)
    {
        switch (model)
        {
        case Model::ArcadeOriginal: return "ARCADE_ORIGINAL";
        case Model::ArcadeHybrid: return "ARCADE_HYBRID";
        case Model::PS2OriginalExperimental: return "PS2_ORIGINAL_EXPERIMENTAL";
        default: return "MODERN_DD";
        }
    }

    inline bool model_uses_modern_sat(Model model)
    {
        return model == Model::ModernDD || model == Model::ArcadeHybrid;
    }

    inline bool model_uses_arcade_events(Model model)
    {
        return model == Model::ArcadeOriginal || model == Model::ArcadeHybrid;
    }

    inline bool model_uses_original_condition_backbone(Model model)
    {
        return model == Model::ArcadeOriginal ||
               model == Model::PS2OriginalExperimental;
    }

    // Boomslangnz/FFBArcadePlugin OutRun2Real.cpp derives a 10%-step
    // SpeedStrength from Lindbergh's speed value: 0.1..80=>10%, 80.1..130=>20%,
    // 130.1..180=>30%, 180.1..220=>40%, 220.1..270=>50%, 270.1..320=>60%,
    // 320.1..380=>70%, 380.1..430=>80%, 430.1..500=>90%, >500=>100%.
    // C2C exposes a different speed scale, so normalize those thresholds to the
    // established C2C speedNorm (top-speed region ~= 1.0). This preserves the
    // observed arcade step structure without importing Lindbergh addresses.
    constexpr float ArcadeRoadSinePeriodMs = 70.0f;
    constexpr float ArcadeGearSinePeriodMs = 240.0f;
    constexpr float ArcadeGearSineAmplitude = 0.10f;
    constexpr int ArcadeGearEventFrames = 15; // ceil(240 ms * 60 Hz)
    constexpr float ArcadeConstantEventLengthMs = 80.0f;
    constexpr int ArcadeConstantEventFrames = 5; // nearest 60 Hz frame count

    // Host-only emergency crash fallback. The game's collision-state edge is
    // authoritative; these thresholds only catch severe deceleration when that
    // witness is absent. They are tuned from captured PC runtime telemetry.
    constexpr float CrashFallbackSpeedDropMin = 0.12f;
    constexpr float CrashFallbackSpeedDropFull = 0.36f;
    constexpr float CrashFallbackCurrentSpeedMin = 0.10f;

    inline bool crash_speed_drop_fallback(
        float speedDrop,
        float currentSpeed)
    {
        return std::isfinite(speedDrop) && std::isfinite(currentSpeed) &&
            currentSpeed > CrashFallbackCurrentSpeedMin &&
            speedDrop > CrashFallbackSpeedDropMin;
    }

    inline float crash_speed_drop_severity(float speedDrop)
    {
        if (!std::isfinite(speedDrop))
            return 0.0f;
        return std::clamp(
            (speedDrop - CrashFallbackSpeedDropMin) /
                (CrashFallbackSpeedDropFull - CrashFallbackSpeedDropMin),
            0.0f, 1.0f);
    }

    // OR2006C2C course-collision response sets EVWORK_CAR::field_283 to
    // 0x1E (30) from FUN_00503a20. Treat only a high-value reload/rising edge
    // as a new course/wall contact so sustained scraping cannot retrigger every tick.
    constexpr unsigned CourseCollisionTimerReload = 0x1Eu;
    constexpr unsigned CourseCollisionTimerEdgeFloor = 0x1Cu;

    inline bool course_collision_timer_edge(unsigned currentTimer, unsigned previousTimer)
    {
        return currentTimer >= CourseCollisionTimerEdgeFloor &&
            currentTimer > previousTimer;
    }


    inline float frequency_hz_from_period_ms(float periodMs)
    {
        if (!std::isfinite(periodMs) || periodMs <= 0.0f)
            return 0.0f;
        return 1000.0f / periodMs;
    }

    inline float arcade_gear_sine_force(
        int elapsedFrame,
        float hostScale)
    {
        if (elapsedFrame < 0 || elapsedFrame >= ArcadeGearEventFrames)
            return 0.0f;
        hostScale = std::isfinite(hostScale)
            ? std::clamp(hostScale, 0.0f, 1.0f) : 0.0f;
        constexpr float TwoPi = 6.28318530718f;
        const float elapsedMs =
            static_cast<float>(elapsedFrame) * (1000.0f / 60.0f);
        const float phase =
            TwoPi * elapsedMs / ArcadeGearSinePeriodMs;
        return std::sin(phase) * ArcadeGearSineAmplitude * hostScale;
    }

    inline float compose_arcade_directional_surface(
        float sustainedForce,
        float transitionForce,
        bool transitionActive)
    {
        if (!std::isfinite(sustainedForce))
            sustainedForce = 0.0f;
        if (!std::isfinite(transitionForce))
            transitionForce = 0.0f;
        // A Lindbergh callback carries one force code. During the reconstructed
        // short 0x04/0x14 transition, that code owns the directional output
        // rather than summing with a simultaneous 0x10/0x00 reconstruction.
        return transitionActive ? transitionForce : sustainedForce;
    }

    inline float arcade_speed_strength(float speedNorm)
    {
        if (!std::isfinite(speedNorm) || speedNorm <= 0.0f)
            return 0.0f;
        speedNorm = std::clamp(speedNorm, 0.0f, 1.25f);
        if (speedNorm <= 0.16f) return 0.10f;
        if (speedNorm <= 0.26f) return 0.20f;
        if (speedNorm <= 0.36f) return 0.30f;
        if (speedNorm <= 0.44f) return 0.40f;
        if (speedNorm <= 0.54f) return 0.50f;
        if (speedNorm <= 0.64f) return 0.60f;
        if (speedNorm <= 0.76f) return 0.70f;
        if (speedNorm <= 0.86f) return 0.80f;
        if (speedNorm <= 1.00f) return 0.90f;
        return 1.00f;
    }

    inline float smoothstep01(float t)
    {
        t = std::clamp(t, 0.0f, 1.0f);
        return t * t * (3.0f - 2.0f * t);
    }

    struct EngineHapticEstimate
    {
        float rpmNorm = 0.0f;
        float frequencyHz = 0.0f;
        float amplitudeScale = 0.0f;
    };

    // OutRun does not expose a verified engine-RPM field in EVWORK_CAR yet.
    // Estimate normalized RPM from vehicle speed, current gear and throttle so
    // the haptic can be swapped to a real RPM source later without changing the
    // output path or UI. Frequencies stay below 20 Hz for a stable 60 Hz FFB loop.
    inline EngineHapticEstimate estimate_engine_haptics(
        float speedNorm, unsigned int gear, float throttleNorm)
    {
        speedNorm = std::isfinite(speedNorm)
            ? std::clamp(speedNorm, 0.0f, 1.0f) : 0.0f;
        throttleNorm = std::isfinite(throttleNorm)
            ? std::clamp(throttleNorm, 0.0f, 1.0f) : 0.0f;

        // Approximate normalized road speed at redline for gears 1..6.
        // Only the relative drop/rise matters for tactile frequency shaping.
        static constexpr std::array<float, 6> GearRedlineSpeed = {
            0.17f, 0.30f, 0.44f, 0.60f, 0.78f, 1.00f
        };
        const unsigned int forwardGear = std::clamp(gear, 1u, 6u);
        const float coupledRpm =
            speedNorm / GearRedlineSpeed[forwardGear - 1u];
        const float idleFloor = 0.10f + 0.05f * throttleNorm;
        const float freeRev = (gear == 0 || speedNorm < 0.025f)
            ? 0.10f + 0.55f * throttleNorm
            : 0.0f;

        EngineHapticEstimate out{};
        out.rpmNorm = std::clamp(
            std::max({ coupledRpm, idleFloor, freeRev }), 0.08f, 1.0f);
        // Keep the texture above the heavy low-frequency pulse region while
        // remaining below the 60 Hz FFB loop Nyquist limit.
        out.frequencyHz = 13.0f + 11.0f * out.rpmNorm;
        out.amplitudeScale = std::clamp(
            0.45f + 0.40f * out.rpmNorm + 0.15f * throttleNorm,
            0.0f, 1.0f);
        return out;
    }

    // Saturating proxy for front-tyre lateral force. OutRun does not expose
    // per-tyre Fy, so use front slip only for the curve shape and keep the
    // game's lateral signal as a separate load modifier in WheelFFBEngine.
    // The 0.20 rad scale is deliberately broad: normal loaded corners remain
    // progressive while deep understeer approaches a force plateau.
    inline float lateral_force_shape(float alpha)
    {
        if (!std::isfinite(alpha)) return 0.0f;
        constexpr float HalfPi = 1.57079632679f;
        const float x = std::clamp(std::abs(alpha) / 0.20f, 0.0f, 1.0f);
        return std::sin(x * HalfPi);
    }

    // Pneumatic trail remains near full in the linear tyre region, then falls
    // as slip grows. Keep a small residual rather than forcing the pneumatic
    // lever arm mathematically to zero because this is an arcade-state proxy,
    // not a fitted tyre dataset.
    inline float pneumatic_trail_factor(float alpha)
    {
        if (!std::isfinite(alpha)) return 0.0f;
        constexpr float FullTrailUntil = 0.08f;
        constexpr float TrailFallComplete = 0.42f;
        constexpr float ResidualTrail = 0.15f;
        const float t = smoothstep01(
            (std::abs(alpha) - FullTrailUntil) /
            (TrailFallComplete - FullTrailUntil));
        return 1.0f - (1.0f - ResidualTrail) * t;
    }

    // Reference peak of Fy * pneumatic trail. The absolute units are not
    // available from OutRun, so this keeps SteeringWeight near its established
    // scale while the relative trail terms shape the torque curve.
    inline constexpr float PneumaticReferencePeak = 0.838899081f;

    // Lateral force and pneumatic trail have different transient behaviour.
    // forceAlpha is the filtered tyre-force slip, while trailAlpha may be a
    // modest phase-led version used only by the pneumatic lever arm.
    inline float pneumatic_sat_shape(float forceAlpha, float trailAlpha)
    {
        if (!std::isfinite(forceAlpha) || !std::isfinite(trailAlpha)) return 0.0f;
        const float raw =
            lateral_force_shape(forceAlpha) * pneumatic_trail_factor(trailAlpha);
        return std::clamp(raw / PneumaticReferencePeak, 0.0f, 1.0f);
    }

    inline float pneumatic_sat_shape(float alpha)
    {
        return pneumatic_sat_shape(alpha, alpha);
    }

    // Mechanical/caster trail contributes whenever front lateral force exists;
    // it is not a substitute that appears only after pneumatic trail collapses.
    // The setting is a normalized pseudo-trail ratio, not a physical distance.
    inline float mechanical_sat_shape(float forceAlpha, float mechanicalTrailRatio)
    {
        if (!std::isfinite(forceAlpha)) return 0.0f;
        const float ratio = std::clamp(mechanicalTrailRatio, 0.0f, 0.60f);
        const float denominator = PneumaticReferencePeak + ratio;
        return denominator > 0.0f
            ? std::clamp(lateral_force_shape(forceAlpha) * ratio / denominator, 0.0f, 1.0f)
            : 0.0f;
    }

    // Keep normal-corner feel unchanged, then add only the missing
    // mechanical/caster self-steer in a large drift. Pneumatic trail and the
    // existing re-grip/return suppression are deliberately untouched.
    constexpr float DeepSlipMechanicalBoost = 1.25f;
    constexpr float DeepSlipMechanicalStartRad = 0.18f;
    constexpr float DeepSlipMechanicalFullRad = 0.32f;

    inline float deep_slip_mechanical_trail_ratio(float forceAlpha, float mechanicalTrailRatio)
    {
        const float ratio = std::isfinite(mechanicalTrailRatio)
            ? std::clamp(mechanicalTrailRatio, 0.0f, 0.60f) : 0.0f;
        if (!std::isfinite(forceAlpha))
            return ratio;

        const float t = std::clamp(
            (std::abs(forceAlpha) - DeepSlipMechanicalStartRad) /
                (DeepSlipMechanicalFullRad - DeepSlipMechanicalStartRad),
            0.0f, 1.0f);
        const float smooth = t * t * (3.0f - 2.0f * t);
        return std::clamp(
            ratio * (1.0f + (DeepSlipMechanicalBoost - 1.0f) * smooth),
            0.0f, 0.60f);
    }

    // Total aligning moment follows Fy * (pneumatic trail + mechanical trail).
    // Normalize the total pseudo-trail so enabling mechanical trail reshapes
    // the SAT curve without silently turning SteeringWeight into a second gain.
    inline float combined_sat_shape(
        float forceAlpha, float trailAlpha, float mechanicalTrailRatio)
    {
        if (!std::isfinite(forceAlpha) || !std::isfinite(trailAlpha)) return 0.0f;
        const float ratio = std::clamp(mechanicalTrailRatio, 0.0f, 0.60f);
        const float denominator = PneumaticReferencePeak + ratio;
        if (denominator <= 0.0f)
            return 0.0f;
        const float raw = lateral_force_shape(forceAlpha) *
            (pneumatic_trail_factor(trailAlpha) + ratio);
        return std::clamp(raw / denominator, 0.0f, 1.0f);
    }

    inline float combined_sat_shape(float alpha, float mechanicalTrailRatio)
    {
        return combined_sat_shape(alpha, alpha, mechanicalTrailRatio);
    }

    // Kept as a compatibility alias for older host tests/tools. Production
    // Physics SAT uses the decomposed functions above explicitly.
    inline float trail_shape(float alpha)
    {
        return pneumatic_sat_shape(alpha);
    }

    // Symmetric C1 soft limiter. Preserve low/mid-range force exactly, then
    // bend only the final quarter toward the DirectInput cap. This keeps SAT
    // detail and weight intact while still preventing hard clipping at 100%.
    inline float soft_saturate(float value)
    {
        if (!std::isfinite(value)) return 0.0f;
        const float sign = value < 0.0f ? -1.0f : 1.0f;
        const float x = std::abs(value);
        constexpr float Knee = 0.75f;
        constexpr float Limit = 1.35f;
        if (x <= Knee) return value;
        if (x >= Limit) return sign;

        const float span = Limit - Knee;
        const float t = (x - Knee) / span;
        const float t2 = t * t;
        const float t3 = t2 * t;
        const float h00 = 2.0f * t3 - 3.0f * t2 + 1.0f;
        const float h10 = t3 - 2.0f * t2 + t;
        const float h01 = -2.0f * t3 + 3.0f * t2;
        const float y = h00 * Knee + h10 * span + h01;
        return sign * y;
    }

    inline float physics_return_relief(float alpha, float steerRate)
    {
        // Relieve only torque doing positive work on the moving wheel.
        // Steering centre is irrelevant to front-tyre SAT direction.
        const float t = -alpha * steerRate > 0.0f
            ? std::clamp(std::abs(steerRate) / 0.08f, 0.0f, 1.0f) : 0.0f;
        return 1.0f - 0.15f * t*t*(3.0f - 2.0f*t);
    }

    using ResponseLUT = std::array<float, 11>;

    inline ResponseLUT linear_response_lut()
    {
        ResponseLUT lut{};
        for (size_t i = 0; i < lut.size(); ++i)
            lut[i] = static_cast<float>(i) / 10.0f;
        return lut;
    }

    // Eleven output-command samples for desired torque 0%, 10%, ... 100%.
    // The curve must be monotonic, start at zero and finish at full scale.
    inline bool parse_response_lut(std::string_view spec, ResponseLUT& out)
    {
        std::stringstream stream{std::string(spec)};
        ResponseLUT parsed{};
        for (size_t i = 0; i < parsed.size(); ++i)
        {
            std::string token;
            if (!std::getline(stream, token, ','))
                return false;
            std::stringstream valueStream{token};
            float value = 0.0f;
            if (!(valueStream >> value) || !std::isfinite(value) ||
                value < 0.0f || value > 1.0f)
                return false;
            valueStream >> std::ws;
            if (!valueStream.eof())
                return false;
            if (i > 0 && value + 0.000001f < parsed[i - 1])
                return false;
            parsed[i] = value;
        }

        std::string extra;
        if (std::getline(stream, extra, ','))
        {
            if (extra.find_first_not_of(" \t\r\n") != std::string::npos)
                return false;
        }
        if (parsed.front() > 0.001f || parsed.back() < 0.999f)
            return false;
        out = parsed;
        return true;
    }

    inline std::string format_response_lut(const ResponseLUT& lut)
    {
        std::ostringstream stream;
        stream << std::fixed << std::setprecision(3);
        for (size_t i = 0; i < lut.size(); ++i)
        {
            if (i) stream << ',';
            stream << std::clamp(lut[i], 0.0f, 1.0f);
        }
        return stream.str();
    }

    inline float apply_response_lut(float value, const ResponseLUT& lut)
    {
        if (!std::isfinite(value)) return 0.0f;
        const float sign = value < 0.0f ? -1.0f : 1.0f;
        const float x = std::clamp(std::abs(value), 0.0f, 1.0f);
        const float scaled = x * 10.0f;
        const size_t index = std::min<size_t>(9, static_cast<size_t>(scaled));
        const float fraction = std::clamp(scaled - static_cast<float>(index), 0.0f, 1.0f);
        const float y = lut[index] + (lut[index + 1] - lut[index]) * fraction;
        return sign * std::clamp(y, 0.0f, 1.0f);
    }
}
