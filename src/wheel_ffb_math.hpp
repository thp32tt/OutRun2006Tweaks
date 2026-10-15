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
        RetiredLegacyModel2 = 2,
        PS2OriginalExperimental = 3,
    };

    inline Model sanitize_model(int value)
    {
        // R10 follow-up: Hybrid is retired from the selectable/runtime model set.
        // Preserve legacy numeric compatibility by treating saved Model=2 as
        // Modern DD; Model=3 remains PS2 so old profiles do not renumber.
        if (value == 2)
            return Model::ModernDD;
        if (value <= 0)
            return Model::ModernDD;
        if (value == 1)
            return Model::ArcadeOriginal;
        return Model::PS2OriginalExperimental;
    }

    inline const char* model_name(Model model)
    {
        switch (model)
        {
        case Model::ArcadeOriginal: return "ARCADE_ORIGINAL";
        case Model::PS2OriginalExperimental: return "PS2_ORIGINAL_EXPERIMENTAL";
        default: return "MODERN_DD";
        }
    }

    inline bool model_uses_modern_sat(Model model)
    {
        return model == Model::ModernDD;
    }

    inline bool model_uses_arcade_events(Model model)
    {
        return model == Model::ArcadeOriginal;
    }

    inline bool model_uses_original_condition_backbone(Model model)
    {
        return model == Model::ArcadeOriginal ||
               model == Model::PS2OriginalExperimental;
    }

    // MOZA R3 hardware A/B establishes opposite DirectInput polarity families:
    // Modern DD needs both output and Spring reversed, while Arcade/PS2
    // use the backend's native signs.  Keep this model rule in one place so
    // profile/UI/runtime paths cannot drift apart again.
    inline bool model_uses_reversed_r3_polarity(Model model)
    {
        return model == Model::ModernDD;
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

    // Brush-model-inspired pneumatic trail: keep the lever arm near full in the
    // linear tyre region, then let it collapse almost completely once the front
    // contact patch is fully sliding. Any useful high-slip remainder is modelled
    // separately as residual aligning moment instead of hiding it in trail.
    inline float pneumatic_trail_factor(float alpha)
    {
        if (!std::isfinite(alpha)) return 0.0f;
        constexpr float FullTrailUntil = 0.08f;
        constexpr float TrailFallComplete = 0.425f;
        constexpr float ResidualTrail = 0.02f;
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

    // R13 keeps mechanical/caster trail geometric. Deep slip changes the tyre
    // force, not the steering geometry, so do not invent extra trail as a drift
    // assist. Keep the legacy helper name for profile/test compatibility.
    inline float deep_slip_mechanical_trail_ratio(float forceAlpha, float mechanicalTrailRatio)
    {
        (void)forceAlpha;
        return std::isfinite(mechanicalTrailRatio)
            ? std::clamp(mechanicalTrailRatio, 0.0f, 0.60f) : 0.0f;
    }

    // Once the chassis is in a developed drift, front-wheel slip is no longer
    // a reliable torque-direction owner: the rack may already be crossing through
    // countersteer while alpha_f has the opposite sign. Use body slip as the
    // steering-direction authority in that state and crossfade fully to it.
    // Ordinary cornering still uses front-slip SAT because the body-slip gate is 0.
    constexpr float DriftCountersteerStartRad = 0.16f;
    constexpr float DriftCountersteerFullRad = 0.42f;
    constexpr float DriftCountersteerMaxBlend = 1.00f;
    constexpr float DefaultCountersteerStrength = 0.72f;

    inline float drift_countersteer_blend(
        float bodySlip, float frontSlip, float bodySlide)
    {
        if (!std::isfinite(bodySlip) || !std::isfinite(frontSlip) ||
            !std::isfinite(bodySlide))
            return 0.0f;

        const float slipT = smoothstep01(
            (std::abs(bodySlip) - DriftCountersteerStartRad) /
                (DriftCountersteerFullRad - DriftCountersteerStartRad));
        const float slideT = smoothstep01(
            (std::clamp(bodySlide, 0.0f, 1.0f) - 0.20f) / 0.55f);
        return DriftCountersteerMaxBlend * slipT * slideT;
    }

    inline float drift_countersteer_blend_state_step(
        float currentBlend, float targetBlend)
    {
        if (!std::isfinite(currentBlend))
            currentBlend = 0.0f;
        if (!std::isfinite(targetBlend))
            targetBlend = 0.0f;
        currentBlend = std::clamp(currentBlend, 0.0f, 1.0f);
        targetBlend = std::clamp(targetBlend, 0.0f, 1.0f);

        // Enter countersteer quickly, but release it more gently while grip
        // returns.  The asymmetric release prevents a one/two-frame body-slip
        // sign change from snapping the rack through centre and rebounding.
        constexpr float AttackPerTick = 0.30f;
        constexpr float ReleasePerTick = 0.06f;
        const float delta = targetBlend - currentBlend;
        const float step = delta >= 0.0f ? AttackPerTick : ReleasePerTick;
        return currentBlend + std::clamp(delta, -step, step);
    }

    inline float drift_countersteer_direction_latch(
        float bodySlip, float currentDirection, float currentBlend)
    {
        if (!std::isfinite(currentDirection) ||
            std::abs(currentDirection) < 0.5f)
            currentDirection = 0.0f;
        if (!std::isfinite(bodySlip))
            return currentDirection;

        const float candidate = bodySlip > 0.0f
            ? -1.0f
            : (bodySlip < 0.0f ? 1.0f : currentDirection);

        // Once a developed drift owns rack direction, hold that direction until
        // the handoff has almost released.  This adds hysteresis specifically to
        // grip recovery without delaying the initial countersteer direction.
        constexpr float RelatchBlendThreshold = 0.12f;
        if (currentDirection == 0.0f ||
            currentBlend <= RelatchBlendThreshold)
            return candidate;
        return currentDirection;
    }

    inline float drift_countersteer_shape(float bodySlip)
    {
        if (!std::isfinite(bodySlip))
            return 0.0f;
        const float t = smoothstep01(
            (std::abs(bodySlip) - 0.12f) / 0.38f);
        return t > 0.0f ? 0.45f + 0.45f * t : 0.0f;
    }

    // Body-slip is only a bounded recovery cue. Its absolute torque must not
    // exceed the front-slip SAT that owns steering direction; otherwise a small
    // blend factor can still reverse the result when deep-slip SAT is weak.
    inline float bound_drift_countersteer_torque(
        float primaryFrontSlipTorque, float bodySlipCueTorque)
    {
        if (!std::isfinite(primaryFrontSlipTorque))
            return 0.0f;
        if (!std::isfinite(bodySlipCueTorque))
            return primaryFrontSlipTorque;
        const float limit = std::abs(primaryFrontSlipTorque);
        return std::clamp(bodySlipCueTorque, -limit, limit);
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
        const float fyShape = lateral_force_shape(forceAlpha);
        // Residual Mz is a small high-slip aligning cue, kept separate from
        // pneumatic trail so a fully sliding contact patch does not pretend to
        // retain a large pneumatic lever arm.
        constexpr float ResidualMzRatio = 0.05f;
        const float residualT = smoothstep01(
            (std::abs(forceAlpha) - 0.18f) / 0.24f);
        const float residualMz = fyShape * ResidualMzRatio * residualT;
        const float raw =
            fyShape * (pneumatic_trail_factor(trailAlpha) + ratio) +
            residualMz;
        return std::clamp(raw / denominator, 0.0f, 1.0f);
    }

    inline float combined_sat_shape(float alpha, float mechanicalTrailRatio)
    {
        return combined_sat_shape(alpha, alpha, mechanicalTrailRatio);
    }

    inline float combined_sat_shape_with_deep_slip_boost(
        float forceAlpha, float trailAlpha, float baseMechanicalTrailRatio)
    {
        // Legacy API name retained for existing callers/tests. R13 deliberately
        // removes slip-dependent mechanical boost and uses the geometric model.
        return combined_sat_shape(
            forceAlpha, trailAlpha, baseMechanicalTrailRatio);
    }

    inline float impact_direction_from_lateral(float lateral, float deadband = 0.04f)
    {
        if (!std::isfinite(lateral) || std::abs(lateral) <= std::max(0.0f, deadband))
            return 0.0f;
        return lateral > 0.0f ? -1.0f : 1.0f;
    }

    constexpr unsigned PrimaryAsphaltSurfaceMask = 0x00000002u;
    constexpr unsigned PrimaryRoughRoadSurfaceMask = 0x00100000u;
    constexpr unsigned PrimarySnowIceSurfaceMask = 0x00800000u;

    // R10 R3 hardware retune. R9's 0.04 snow/ice comfort factor reduced a
    // rough=0.50 road to roughly 0.011 roadAmp in the supplied run, effectively
    // erasing the surface. 22% keeps sustained snow/rough paving comfortable
    // while leaving a clearly perceptible low-amplitude texture.
    constexpr float SnowIceComfortTextureScale = 0.22f;

    inline bool proven_primary_rough_road_section(int uniqueStage, int roadSection)
    {
        return (uniqueStage == 1 && roadSection >= 419 && roadSection <= 458) ||
               (uniqueStage == 10 && roadSection >= 54 && roadSection <= 70) ||
               (uniqueStage == 27 && roadSection >= 510 && roadSection <= 533);
    }

    inline bool is_proven_primary_rough_road_contact(
        int uniqueStage, int roadSection, unsigned surfaceMask)
    {
        return surfaceMask == PrimaryRoughRoadSurfaceMask &&
            proven_primary_rough_road_section(uniqueStage, roadSection);
    }


    // R9 runtime-log fix: several water-capable stages report mask 0x2 as a
    // water material even while every wheel is on the ordinary primary road.
    // Treat only the unambiguous all-four / collision-context-zero case as the
    // primary-asphalt false positive. Actual mixed/water contacts remain intact.
    inline bool primary_asphalt_water_false_positive(
        int uniqueStage,
        int collisionContext,
        const std::array<unsigned, 4>& masks,
        unsigned waterWheelMask)
    {
        // Hardware evidence currently proves this false-positive only on
        // Imperial Avenue (unique stage 14). Keep other water-capable stages
        // untouched until their own runtime traces establish the same case.
        if (uniqueStage != 14 ||
            collisionContext != 0 || waterWheelMask != 0x0Fu)
            return false;
        for (unsigned mask : masks)
            if (mask != PrimaryAsphaltSurfaceMask)
                return false;
        return true;
    }

    constexpr unsigned ImperialAvenueCompanionPavingMask = 0x00000800u;

    // R14 hardware evidence: Imperial Avenue's normal roadway is stone/brick
    // for the whole stage, while the game alternates the same road between 0x2
    // and 0x800 per wheel. Requiring a live 0x800 sample made the tactile carrier
    // drop out whenever a frame happened to be all-0x2. Treat the whole verified
    // 0x2/0x800 family as one continuous primary stone road. collisionContext==0
    // keeps actual collision/water contexts outside this override.
    inline bool imperial_avenue_stone_paving_pattern(
        int uniqueStage,
        int collisionContext,
        const std::array<unsigned, 4>& masks)
    {
        if (uniqueStage != 14 || collisionContext != 0)
            return false;
        for (unsigned mask : masks)
        {
            if (mask != ImperialAvenueCompanionPavingMask &&
                mask != PrimaryAsphaltSurfaceMask)
                return false;
        }
        return true;
    }

    inline float imperial_avenue_stone_tactile_amplitude(
        float speedNorm,
        float roadSetting,
        float outputStrength)
    {
        if (!std::isfinite(speedNorm) || !std::isfinite(roadSetting) ||
            !std::isfinite(outputStrength))
            return 0.0f;
        const float speedGate = smoothstep01(
            (std::clamp(speedNorm, 0.0f, 1.0f) - 0.04f) / 0.30f);
        const float roadScale = std::clamp(roadSetting / 0.60f, 0.0f, 1.67f);
        const float gainScale = std::clamp(outputStrength / 0.70f, 0.0f, 2.0f);
        // R17 hardware follow-up: even the R16 ~0.20 tune felt stronger
        // than curb/shoulder contact on the R3. Keep Imperial Avenue as a
        // subtle full-stage stone texture only; curb/off-road must remain the
        // clearly stronger tactile event. The final road_motion_gate() still
        // removes this channel entirely at standstill and fades it in with speed.
        return std::clamp(
            (0.020f + 0.030f * speedGate) * roadScale * gainScale,
            0.0f, 0.05f);
    }

    // Road texture is contact texture, so it must disappear when the car is
    // stationary.  Apply this at the final road channel for every model rather
    // than baking special stop logic into individual stage/material classifiers.
    inline float road_motion_gate(float speedNorm)
    {
        if (!std::isfinite(speedNorm))
            return 0.0f;
        return smoothstep01(
            (std::clamp(speedNorm, 0.0f, 1.0f) - 0.005f) / 0.075f);
    }


    // Common PC/DD contact layer used only to make the physically obvious
    // 0/1/2/3/4-wheel contact states distinguishable.  It does not replace the
    // Lindbergh or PS2 source-model effects; those remain the primary model
    // semantics and this envelope fills otherwise silent curb/transition cases.
    inline float contact_tactile_envelope(
        const std::array<float, 4>& wheelRoughness,
        unsigned waterWheelMask)
    {
        float sum = 0.0f;
        for (int i = 0; i < 4; ++i)
        {
            if ((waterWheelMask & (1u << i)) != 0)
                continue;
            const float r = std::isfinite(wheelRoughness[i])
                ? wheelRoughness[i] : 0.25f;
            const float excess = std::clamp(
                (r - 0.25f) / 0.60f, 0.0f, 1.0f);
            sum += std::sqrt(excess);
        }
        // Average preserves wheel count, while 2x gain makes a two-wheel curb
        // clearly tactile without letting full-width rough pavement exceed 1.0.
        return std::clamp((sum * 0.25f) * 2.0f, 0.0f, 1.0f);
    }

    inline float common_contact_tactile_amplitude(
        float contactEnvelope,
        float speedNorm,
        float roadSetting,
        float outputStrength)
    {
        if (!std::isfinite(contactEnvelope) || !std::isfinite(speedNorm) ||
            !std::isfinite(roadSetting) || !std::isfinite(outputStrength))
            return 0.0f;
        const float speedGate = smoothstep01(
            (std::clamp(speedNorm, 0.0f, 1.0f) - 0.04f) / 0.18f);
        const float roadScale = std::clamp(roadSetting / 0.60f, 0.0f, 1.67f);
        const float gainScale = std::clamp(outputStrength / 0.70f, 0.0f, 2.0f);
        return std::clamp(
            0.28f * std::clamp(contactEnvelope, 0.0f, 1.0f) *
                speedGate * roadScale * gainScale,
            0.0f, 0.32f);
    }

    inline float modern_road_tactile_amplitude(
        bool imperialStonePaving,
        float commonContactTactile,
        float imperialStoneTactile)
    {
        if (!std::isfinite(commonContactTactile))
            commonContactTactile = 0.0f;
        if (!std::isfinite(imperialStoneTactile))
            imperialStoneTactile = 0.0f;
        const float common = std::clamp(commonContactTactile, 0.0f, 1.0f);
        const float imperial = std::clamp(imperialStoneTactile, 0.0f, 1.0f);
        // Imperial Avenue is a sustained primary-road texture, not a curb.
        // Do not let the generic 4-wheel contact layer (~0.23 at roughness 0.35)
        // dominate its deliberately subtle ~0.05 stone carrier.
        return imperialStonePaving ? imperial : common;
    }

    // Direction-independent collision texture.  The directional rack kick is
    // still model-owned; this alternating pulse guarantees that a head-on wall
    // hit is tactile even when the lateral-direction estimator correctly returns
    // zero.  PS2 uses this as an explicit PC host assist, not a claimed retail
    // ConstantForce event.
    inline float collision_tactile_pulse(int impactFrame, float hostScale)
    {
        static constexpr std::array<float, 6> Pattern = {
            0.90f, -0.68f, 0.50f, -0.36f, 0.24f, -0.14f
        };
        if (impactFrame < 0 || impactFrame >= static_cast<int>(Pattern.size()))
            return 0.0f;
        hostScale = std::isfinite(hostScale)
            ? std::clamp(hostScale, 0.0f, 1.0f) : 0.0f;
        return Pattern[static_cast<size_t>(impactFrame)] * hostScale;
    }

    inline float software_road_tactile_frequency(float requestedHz)
    {
        if (!std::isfinite(requestedHz) || requestedHz <= 0.0f) return 0.0f;
        return std::min(requestedHz, 10.0f);
    }

    inline float software_slip_tactile_frequency(float requestedHz)
    {
        if (!std::isfinite(requestedHz) || requestedHz <= 0.0f) return 0.0f;
        return std::min(requestedHz, 12.0f);
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
        // Relieve only torque already accelerating the rack in the aligning
        // direction.  R8's 15% release noticeably hid DD self-countersteer.
        // Keep a small anti-whip relief in normal corners, but retain nearly all
        // aligning torque once front slip is large enough to require recovery.
        const float t = -alpha * steerRate > 0.0f
            ? std::clamp(std::abs(steerRate) / 0.08f, 0.0f, 1.0f) : 0.0f;
        const float deepSlipT = smoothstep01(
            (std::abs(alpha) - 0.14f) / 0.12f);
        const float maxRelief = 0.10f + (0.03f - 0.10f) * deepSlipT;
        return 1.0f - maxRelief * t*t*(3.0f - 2.0f*t);
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
