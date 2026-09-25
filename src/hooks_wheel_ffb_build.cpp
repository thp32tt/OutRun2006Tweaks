// Build shim for the experimental WheelFFB implementation.
// Keep NOMINMAX local to this translation unit so Windows min/max macros do not
// collide with std::min/std::max/std::clamp in the DirectInput FFB engine.
#define NOMINMAX

// Compile the core through two narrow compatibility aliases. The surface alias
// lets this shim provide a temporary roughness floor only while a snow curb is
// latched; the original game surface LUT remains authoritative everywhere else.
#define sub_1149C0 WheelFFB_SurfaceRoughnessForCore
#define WheelFFB_UpdateAfterPhysics WheelFFB_UpdateAfterPhysics_Core
#include "hooks_wheel_ffb.cpp"
#undef WheelFFB_UpdateAfterPhysics
#undef sub_1149C0

#include "input_manager.hpp"
#include "hooks_wheel_input_compat_v2.hpp"
#include "hooks_wheel_r3_menu_dpad.hpp"
#include "hooks_wheel_r3_menu_ab.hpp"
#include "hooks_wheel_r3_device_autoselect.hpp"
#include "hooks_wheel_menu_keyboard_back.hpp"
#include "hooks_wheel_menu_keyboard_select.hpp"
#include "hooks_wheel_legacy_blank_defaults.hpp"

#include <imgui.h>
#include <cstring>

// The core include above declared the macro-renamed surface function. Define it
// here as a transparent pass-through with one optional, one-tick compatibility
// floor. This avoids mutating EVWORK_CAR or weakening the core's normal asphalt
// threshold just to retain a snow curb whose material scalar is below snow.
extern double __cdecl sub_1149C0(
    unsigned int surfaceMask, int loadColiType, DWORD* waterFlag);
namespace
{
    bool coreSurfaceRoughnessFloorActive = false;
    float coreSurfaceRoughnessFloor = 0.0f;
}

double __cdecl WheelFFB_SurfaceRoughnessForCore(
    unsigned int surfaceMask, int loadColiType, DWORD* waterFlag)
{
    const double original = sub_1149C0(surfaceMask, loadColiType, waterFlag);
    if (!coreSurfaceRoughnessFloorActive || !std::isfinite(original))
        return original;
    return std::max(original, static_cast<double>(coreSurfaceRoughnessFloor));
}

// The legacy vibration path lives in hooks_forcefeedback.cpp, but this wheel
// build owns the modern input/FFB integration. Keep its controller routing safe
// without duplicating the large Xbox-derived vibration routine.
namespace Settings
{
    extern Setting<int> VibrationMode;
    extern Setting<int> VibrationControllerId;

    // One-shot migration marker for FFB feel defaults. It is deliberately
    // device-agnostic: wheel model names must never select a different force
    // model or different SAT response.
    Setting<int> WheelFFBFeelRevision{
        "WheelFFB", "FeelRevision", 0,
        "Internal one-shot migration version for wheel FFB feel defaults.",
        Range<int>{ 0, 5 }
    };
}

extern int VibrationUserId;
void SetVibration(int userId, float leftMotor, float rightMotor);
void InputManager_StopVibration();
void InputManager_Update();

namespace
{
    struct StageSurfaceContext
    {
        int stageNumber = -1;
        int uniqueStage = -1;
        const char* name = "Unknown";
        bool snowOrIce = false;
        bool mask2CanMarkWater = false;
        bool mask400000IsLowRoughness = false;
    };

    StageSurfaceContext sample_stage_surface_context()
    {
        StageSurfaceContext result{};
        if (!Game::GetNowStageNum || !Game::GetStageUniqueNum)
            return result;

        result.stageNumber = Game::GetNowStageNum(8);
        result.uniqueStage = Game::GetStageUniqueNum(result.stageNumber);
        if (result.uniqueStage >= 0 && result.uniqueStage < 66)
            result.name = Game::StageNames[result.uniqueStage];

        // These IDs are taken from the game's own stage table and the
        // reconstructed Xbox sub_1149C0 surface LUT.
        result.snowOrIce =
            result.uniqueStage == 4 || result.uniqueStage == 19 ||
            result.uniqueStage == 34 || result.uniqueStage == 49;
        result.mask2CanMarkWater =
            result.uniqueStage == 11 || result.uniqueStage == 13 ||
            result.uniqueStage == 14 || result.uniqueStage == 41 ||
            result.uniqueStage == 43 || result.uniqueStage == 44;
        result.mask400000IsLowRoughness =
            result.uniqueStage == 18 || result.uniqueStage == 48;
        return result;
    }

    int lastLoggedUniqueStage = -999;

    void maybe_log_stage_context(const StageSurfaceContext& stage)
    {
        if (!Settings::WheelFFBDebugLog || stage.uniqueStage < 0 ||
            stage.uniqueStage == lastLoggedUniqueStage)
            return;

        lastLoggedUniqueStage = stage.uniqueStage;
        spdlog::info(
            "WheelFFB STAGE: stageNumber={} unique={} name={} snowIce={} mask2CanMarkWater={} mask400000Low={}",
            stage.stageNumber, stage.uniqueStage, stage.name,
            stage.snowOrIce, stage.mask2CanMarkWater,
            stage.mask400000IsLowRoughness);
    }

    struct RoadSurfaceProfile
    {
        float minimum = 1.0f;
        float maximum = 0.0f;
        float spread = 0.0f;
        float nonWaterMinimum = 1.0f;
        float nonWaterMaximum = 0.0f;
        unsigned int surfaceMask[4]{};
        float wheelRoughness[4]{};
        unsigned int validWheelMask = 0;
        unsigned int waterWheelMask = 0;
        int validSamples = 0;
        int nonWaterSamples = 0;
        int collisionContext = 0;
    };

    RoadSurfaceProfile sample_surface_profile(EVWORK_CAR* car)
    {
        RoadSurfaceProfile result{};
        if (!car)
            return result;

        // Despite the historical EVWORK_CAR member name, water_flag_24C[] is
        // passed by the original Xbox routine as the per-wheel surface mask.
        // sub_1149C0 independently reports whether a given sample is one of the
        // stage-specific water cases through its output flag.
        result.collisionContext =
            static_cast<int>(car->OnRoadPlace_5C.loadColiType_0);

        for (int i = 0; i < 4; ++i)
        {
            result.surfaceMask[i] = car->water_flag_24C[i];
            DWORD wheelWaterFlag = 0;
            const float roughness = static_cast<float>(sub_1149C0(
                result.surfaceMask[i], result.collisionContext,
                &wheelWaterFlag));
            result.wheelRoughness[i] = roughness;
            if (!std::isfinite(roughness))
                continue;

            result.validWheelMask |= (1u << i);
            result.minimum = std::min(result.minimum, roughness);
            result.maximum = std::max(result.maximum, roughness);
            ++result.validSamples;

            if ((wheelWaterFlag & 1u) != 0)
            {
                result.waterWheelMask |= (1u << i);
            }
            else
            {
                result.nonWaterMinimum =
                    std::min(result.nonWaterMinimum, roughness);
                result.nonWaterMaximum =
                    std::max(result.nonWaterMaximum, roughness);
                ++result.nonWaterSamples;
            }
        }

        if (result.validSamples == 0)
        {
            result.minimum = 0.0f;
            result.nonWaterMinimum = 0.0f;
            return result;
        }

        if (result.nonWaterSamples == 0)
            result.nonWaterMinimum = 0.0f;

        result.spread = std::max(0.0f, result.maximum - result.minimum);
        return result;
    }

    // v0.2 snow-curb state. On snow stages a curb can be rougher OR smoother
    // than the ~0.50 snow baseline. Mixed contact tells us which material is the
    // curb; once all four tyres cross onto that same material the old per-frame
    // mixed test disappears. Retain the material identity until the car returns
    // to the snow baseline instead of lowering the global roughness threshold.
    constexpr float SnowSurfaceBaseline = 0.50f;
    constexpr float SnowLatchedCoreRoughnessFloor = 0.85f;
    constexpr DWORD SnowCurbHoldMs = 450;
    bool snowCurbLatched = false;
    float snowCurbMaterial = 0.0f;
    DWORD snowCurbHoldUntil = 0;

    void clear_snow_curb_latch()
    {
        snowCurbLatched = false;
        snowCurbMaterial = 0.0f;
        snowCurbHoldUntil = 0;
    }

    bool update_snow_curb_latch(
        const RoadSurfaceProfile& surface,
        bool snowStage,
        bool mixedSurface,
        DWORD now)
    {
        if (!snowStage || surface.validSamples < 2)
        {
            clear_snow_curb_latch();
            return false;
        }

        // A snow-curb latch may only start from a transition that still contains
        // the real ~0.50 snow baseline. This prevents post-stage asphalt values
        // such as 0.25/0.35 from being reclassified as a new snow curb.
        const bool minimumIsSnowBaseline =
            std::abs(surface.minimum - SnowSurfaceBaseline) <= 0.06f;
        const bool maximumIsSnowBaseline =
            std::abs(surface.maximum - SnowSurfaceBaseline) <= 0.06f;
        const bool mixedTouchesSnowBaseline =
            mixedSurface && (minimumIsSnowBaseline || maximumIsSnowBaseline);

        if (mixedTouchesSnowBaseline)
        {
            float candidate = surface.minimum;
            if (minimumIsSnowBaseline && !maximumIsSnowBaseline)
                candidate = surface.maximum;
            else if (maximumIsSnowBaseline && !minimumIsSnowBaseline)
                candidate = surface.minimum;
            else
            {
                const float minDistance =
                    std::abs(surface.minimum - SnowSurfaceBaseline);
                const float maxDistance =
                    std::abs(surface.maximum - SnowSurfaceBaseline);
                candidate = minDistance >= maxDistance
                    ? surface.minimum
                    : surface.maximum;
            }

            // Only a meaningful departure from snow starts/re-arms the one-shot
            // hold. The hold deadline is never extended by uniform curb contact.
            if (std::abs(candidate - SnowSurfaceBaseline) >= 0.08f)
            {
                snowCurbLatched = true;
                snowCurbMaterial = candidate;
                snowCurbHoldUntil = now + SnowCurbHoldMs;
            }
        }

        if (!snowCurbLatched)
            return false;

        const float uniformValue =
            (surface.minimum + surface.maximum) * 0.5f;
        const bool nearlyUniform = surface.spread < 0.08f;

        // Returning to the normal ~0.50 snow surface ends the latch immediately.
        if (nearlyUniform &&
            std::abs(uniformValue - SnowSurfaceBaseline) <= 0.05f)
        {
            clear_snow_curb_latch();
            return false;
        }

        // A completed curb crossing is retained only for the fixed 450 ms grace
        // period that began at the last confirmed snow<->curb mixed contact.
        // Uniform curb/road contact must never refresh this deadline.
        if (snowCurbHoldUntil != 0 &&
            static_cast<LONG>(now - snowCurbHoldUntil) < 0)
            return true;

        clear_snow_curb_latch();
        return false;
    }

    bool nearly(float value, float expected)
    {
        return std::isfinite(value) && std::abs(value - expected) <= 0.0005f;
    }

    enum class LegacyPreset
    {
        None,
        Physics,
        Natural,
    };

    LegacyPreset detect_legacy_preset()
    {
        const bool common =
            nearly(static_cast<float>(Settings::WheelFFBGlobalStrength), 0.70f) &&
            nearly(static_cast<float>(Settings::WheelFFBSpringStrength), 0.65f) &&
            nearly(static_cast<float>(Settings::WheelFFBSpringSaturation), 0.95f) &&
            nearly(static_cast<float>(Settings::WheelFFBMechanicalTrail), 0.25f) &&
            nearly(static_cast<float>(Settings::WheelFFBTrailResponseLead), 0.25f) &&
            nearly(static_cast<float>(Settings::WheelFFBGripLoss), 0.65f) &&
            nearly(static_cast<float>(Settings::WheelFFBReversalReleaseRate), 0.12f) &&
            nearly(static_cast<float>(Settings::WheelFFBRoadTexture), 0.30f) &&
            nearly(static_cast<float>(Settings::WheelFFBTireSlip), 0.20f) &&
            nearly(static_cast<float>(Settings::WheelFFBWallImpact), 0.38f);

        if (!common)
            return LegacyPreset::None;

        if (Settings::WheelFFBPhysicsSat &&
            nearly(static_cast<float>(Settings::WheelFFBDamperStrength), 0.28f) &&
            nearly(static_cast<float>(Settings::WheelFFBSteeringWeight), 1.45f) &&
            nearly(static_cast<float>(Settings::WheelFFBWeightTransfer), 0.15f) &&
            nearly(static_cast<float>(Settings::WheelFFBSlewRate), 0.040f))
            return LegacyPreset::Physics;

        if (!Settings::WheelFFBPhysicsSat &&
            nearly(static_cast<float>(Settings::WheelFFBDamperStrength), 0.30f) &&
            nearly(static_cast<float>(Settings::WheelFFBSteeringWeight), 1.75f) &&
            nearly(static_cast<float>(Settings::WheelFFBWeightTransfer), 0.20f) &&
            nearly(static_cast<float>(Settings::WheelFFBSlewRate), 0.045f))
            return LegacyPreset::Natural;

        return LegacyPreset::None;
    }

    void apply_universal_physics_preset()
    {
        Settings::WheelFFBEnable = true;
        Settings::WheelFFBPhysicsSat = true;
        Settings::WheelFFBGlobalStrength = 0.70f;
        Settings::WheelFFBSpringStrength = 0.22f;
        Settings::WheelFFBSpringSaturation = 0.55f;
        Settings::WheelFFBDamperStrength = 0.28f;
        Settings::WheelFFBSteeringWeight = 1.60f;
        Settings::WheelFFBMechanicalTrail = 0.30f;
        Settings::WheelFFBTrailResponseLead = 0.40f;
        Settings::WheelFFBGripLoss = 0.65f;
        Settings::WheelFFBWeightTransfer = 0.15f;
        Settings::WheelFFBSlewRate = 0.12f;
        Settings::WheelFFBReversalReleaseRate = 0.30f;
        Settings::WheelFFBRoadTexture = 0.60f;
        Settings::WheelFFBTireSlip = 0.04f;
        Settings::WheelFFBWallImpact = 0.38f;
        Settings::WheelFFBGearShift = 0.60f;
        Settings::WheelFFBEngineVibration = false;
        Settings::WheelFFBEngineIdle = 0.20f;
        Settings::WheelFFBUseHardwareSpring = true;
        Settings::WheelFFBUseHardwareDamper = true;
        Settings::WheelFFBUsePeriodicEffects = false;
        Settings::WheelFFBInvertForce = true;
        Settings::WheelFFBInvertSpring = false;
        Settings::WheelFFBDebugLog = true;
        Settings::VibrationMode = 0;
    }

    void apply_universal_natural_preset()
    {
        Settings::WheelFFBEnable = true;
        Settings::WheelFFBPhysicsSat = false;
        Settings::WheelFFBGlobalStrength = 0.70f;
        Settings::WheelFFBSpringStrength = 0.22f;
        Settings::WheelFFBSpringSaturation = 0.55f;
        Settings::WheelFFBDamperStrength = 0.30f;
        Settings::WheelFFBSteeringWeight = 1.75f;
        Settings::WheelFFBMechanicalTrail = 0.30f;
        Settings::WheelFFBTrailResponseLead = 0.40f;
        Settings::WheelFFBGripLoss = 0.65f;
        Settings::WheelFFBWeightTransfer = 0.20f;
        Settings::WheelFFBSlewRate = 0.12f;
        Settings::WheelFFBReversalReleaseRate = 0.30f;
        Settings::WheelFFBRoadTexture = 0.60f;
        Settings::WheelFFBTireSlip = 0.04f;
        Settings::WheelFFBWallImpact = 0.38f;
        Settings::WheelFFBGearShift = 0.60f;
        Settings::WheelFFBEngineVibration = false;
        Settings::WheelFFBEngineIdle = 0.20f;
        Settings::WheelFFBUseHardwareSpring = true;
        Settings::WheelFFBUseHardwareDamper = true;
        Settings::WheelFFBUsePeriodicEffects = false;
        Settings::WheelFFBInvertForce = true;
        Settings::WheelFFBInvertSpring = false;
        Settings::WheelFFBDebugLog = true;
        Settings::VibrationMode = 0;
    }

    bool normalize_legacy_preset(bool persist)
    {
        const LegacyPreset preset = detect_legacy_preset();
        if (preset == LegacyPreset::None)
            return false;

        if (preset == LegacyPreset::Physics)
            apply_universal_physics_preset();
        else
            apply_universal_natural_preset();

        WheelFFB_ResetHeadroomStats();
        WheelFFB_RequestSettingsTransition();
        if (persist && !Settings::write(Module::UserIniPath))
            spdlog::warn("WheelFFB: universalized a legacy preset for this session but could not persist user.ini");

        spdlog::info(
            "WheelFFB: migrated legacy {} preset to the device-independent v0.2 force tune",
            preset == LegacyPreset::Physics ? "Physics SAT" : "Natural SAT");
        return true;
    }

    DWORD lastRoadCompatibilityLogTick = 0;
}

// Modern DD snow/curb compatibility shaping lives here, but tactile transport
// ownership stays in the model-aware core. UsePeriodicEffects is a live user/
// model setting: Arcade Original/Hybrid can request the observed Sine path and
// PS2 Original can request its recovered Triangle path. If those hardware
// effects are unavailable, the core already falls back safely to ConstantForce.
//
// During a real surface transition, temporarily unload SAT/damping and normalize
// RoadTexture so the tactile signal remains audible under sustained corner load.
// Snow is special because its four-wheel baseline can itself be around 0.50;
// min/max spread plus a short material latch preserves a curb after all tyres
// complete the transition, regardless of whether the curb scalar is higher or
// lower than the snow scalar.
void __cdecl WheelFFB_UpdateAfterPhysics(EVWORK_CAR* car)
{
    // Old named profiles or old F11 presets can still restore the v0.1 values.
    // Recognize only the exact known signatures so arbitrary user tuning remains
    // untouched, then immediately bring those presets onto the universal tune.
    normalize_legacy_preset(true);

    // Do not rewrite WheelFFBUsePeriodicEffects here. Transport ownership is
    // model-aware in the core and the F11 switch is intentionally live.

    const float originalRoadTexture =
        static_cast<float>(Settings::WheelFFBRoadTexture);
    const float originalSteeringWeight =
        static_cast<float>(Settings::WheelFFBSteeringWeight);
    const float originalDamperStrength =
        static_cast<float>(Settings::WheelFFBDamperStrength);

    bool restoreTactileOverrides = false;
    bool applyCoreSurfaceFloor = false;

    if (!car)
        clear_snow_curb_latch();

    StageSurfaceContext stage{};
    if (car)
    {
        stage = sample_stage_surface_context();
        maybe_log_stage_context(stage);
    }

    const WheelFFBMath::Model ffbModel =
        WheelFFBMath::sanitize_model(static_cast<int>(Settings::WheelFFBModel));

    // The compatibility wrapper's normalized curb boost belongs to the Modern
    // DD model only. Arcade/Hybrid/PS2 models own their surface semantics inside
    // the core and must not be pre-shaped by the Modern DD wrapper.
    if (car && ffbModel == WheelFFBMath::Model::ModernDD)
    {
        const RoadSurfaceProfile surface = sample_surface_profile(car);
        const bool rawMixedSurface =
            surface.validSamples >= 2 && surface.spread >= 0.08f;

        // The reconstructed Xbox LUT can mark stage-specific water as a high
        // roughness value (0.73/0.76/0.79). Keep that signal for the core's
        // water/splash path, but do not mistake water for a curb and apply the
        // compatibility layer's SAT/damper unload or fixed curb amplitude.
        const bool nonWaterRough = surface.nonWaterMaximum >= 0.60f;
        const bool waterOnlyRough =
            surface.waterWheelMask != 0 &&
            surface.maximum >= 0.60f && !nonWaterRough;

        // Ordinary route-fork/asphalt material changes (for example 0.25/0.35)
        // are not tactile curbs. A non-snow mixed transition must include a
        // genuinely rough NON-WATER material before the compatibility boost.
        const bool mixedSurface = rawMixedSurface && nonWaterRough;
        const bool fullyRough =
            surface.nonWaterSamples >= 2 &&
            surface.nonWaterMinimum >= 0.60f;

        const DWORD now = GetTickCount();
        const bool snowStage = stage.snowOrIce;
        const bool snowCurbHeld = update_snow_curb_latch(
            surface, snowStage, rawMixedSurface, now);
        const bool strongTactile = mixedSurface || fullyRough || snowCurbHeld;
        const bool tactileSurface = nonWaterRough || snowCurbHeld;

        float desiredRoadAmp = 0.0f;
        float steeringScale = 1.0f;
        float damperScale = 1.0f;

        if (tactileSurface)
        {
            const float speedRaw = std::isfinite(car->field_1C4)
                ? car->field_1C4 : 0.0f;
            const float speedNorm = std::clamp(speedRaw / 2.0f, 0.0f, 1.0f);
            const float roadSpeedGate =
                std::clamp((speedNorm - 0.05f) / 0.20f, 0.0f, 1.0f);

            // A latched snow curb is already a positively identified surface
            // transition. Otherwise only NON-WATER roughness drives the curb
            // compatibility envelope; stage water remains owned by the core.
            const float textureRoughness = snowCurbHeld
                ? 1.0f
                : std::clamp(
                    (surface.nonWaterMaximum - 0.30f) / 0.55f,
                    0.0f, 1.0f);
            const float outputStrength = std::clamp(
                static_cast<float>(Settings::WheelFFBGlobalStrength), 0.0f, 1.5f);
            const float coreStageScale = snowStage ? 0.04f : 1.0f;

            desiredRoadAmp = strongTactile ? 0.30f : 0.22f;
            const float envelope =
                textureRoughness * roadSpeedGate * outputStrength * coreStageScale;
            if (envelope > 0.0005f)
            {
                // This value is temporary for one physics tick and is restored
                // immediately below. Values above the UI range are intentional:
                // they compensate the core's snow attenuation and/or a small
                // material scalar, while the resulting roadAmp stays bounded by
                // desiredRoadAmp and the DirectInput output remains hard capped.
                const float normalizedRoadSetting = desiredRoadAmp / envelope;
                Settings::WheelFFBRoadTexture = std::clamp(
                    std::max(originalRoadTexture, normalizedRoadSetting),
                    0.0f, 120.0f);
            }

            // Only an already-identified snow curb gets the core surface floor.
            // Normal snow, water and ordinary asphalt use the game's exact LUT.
            applyCoreSurfaceFloor = snowCurbHeld;

            // Keep exactly the same SAT/damper relief when the car completes the
            // transition onto a fully rough or latched snow curb/shoulder.
            steeringScale = strongTactile ? 0.72f : 0.80f;
            damperScale = strongTactile ? 0.55f : 0.70f;
            Settings::WheelFFBSteeringWeight =
                originalSteeringWeight * steeringScale;
            Settings::WheelFFBDamperStrength =
                originalDamperStrength * damperScale;
            restoreTactileOverrides = true;
        }

        if (Settings::WheelFFBDebugLog &&
            (tactileSurface || surface.waterWheelMask != 0) &&
            now - lastRoadCompatibilityLogTick >= 750)
        {
            lastRoadCompatibilityLogTick = now;
            spdlog::info(
                "WheelFFB ROAD: stage={} min={:.2f} max={:.2f} spread={:.2f} nonWaterMin={:.2f} nonWaterMax={:.2f} mixed={} fullRough={} snow={} snowLatch={} waterWheels=0x{:X} waterOnlyRough={} masks={:08X}/{:08X}/{:08X}/{:08X} rough={:.2f}/{:.2f}/{:.2f}/{:.2f} collisionCtx={} coreFloor={} targetAmp={:.2f} roadSetting={:.2f} satScale={:.2f} damperScale={:.2f}",
                stage.uniqueStage,
                surface.minimum, surface.maximum, surface.spread,
                surface.nonWaterMinimum, surface.nonWaterMaximum,
                mixedSurface, fullyRough, snowStage, snowCurbHeld,
                surface.waterWheelMask, waterOnlyRough,
                surface.surfaceMask[0], surface.surfaceMask[1],
                surface.surfaceMask[2], surface.surfaceMask[3],
                surface.wheelRoughness[0], surface.wheelRoughness[1],
                surface.wheelRoughness[2], surface.wheelRoughness[3],
                surface.collisionContext, applyCoreSurfaceFloor,
                desiredRoadAmp,
                static_cast<float>(Settings::WheelFFBRoadTexture),
                steeringScale, damperScale);
        }
    }

    coreSurfaceRoughnessFloorActive = applyCoreSurfaceFloor;
    coreSurfaceRoughnessFloor = applyCoreSurfaceFloor
        ? SnowLatchedCoreRoughnessFloor : 0.0f;
    WheelFFB_UpdateAfterPhysics_Core(car);
    coreSurfaceRoughnessFloorActive = false;
    coreSurfaceRoughnessFloor = 0.0f;

    if (restoreTactileOverrides)
    {
        Settings::WheelFFBRoadTexture = originalRoadTexture;
        Settings::WheelFFBSteeringWeight = originalSteeringWeight;
        Settings::WheelFFBDamperStrength = originalDamperStrength;
    }
}

namespace
{
    class VibrationRoutingFix : public Hook
    {
        inline static SafetyHookInline SetVibrationHook = {};
        inline static bool controllerRumbleMayBeActive_ = false;

        static int safe_controller_id()
        {
            return std::clamp(VibrationUserId, 0, 3);
        }

        static void stop_controller_rumble()
        {
            InputManager_StopVibration();
            XINPUT_VIBRATION zero{};
            XInputSetState(safe_controller_id(), &zero);
            controllerRumbleMayBeActive_ = false;
        }

        static void SetVibration_dest(int, float leftMotor, float rightMotor)
        {
            // XInput supports user indexes 0..3. The original gameplay wrapper
            // passed literal 0 here, which ignored VibrationControllerId while
            // UseNewInput was disabled. Always route the legacy call through the
            // configured, validated controller id; SDL ignores this argument.
            const int userId = safe_controller_id();

            if (!Settings::VibrationMode)
            {
                if (controllerRumbleMayBeActive_)
                    stop_controller_rumble();
                return;
            }

            controllerRumbleMayBeActive_ = true;
            SetVibrationHook.ccall<void>(userId, leftMotor, rightMotor);
        }

    public:
        std::string_view description() override
        {
            return "VibrationRoutingFix";
        }

        void declare_settings() override
        {
            // VibrationMode is a live setting. Turning it off must actively
            // clear both SDL and XInput output even if the overlay/menu prevents
            // another player-car physics callback from reaching SetVibration.
            Settings::VibrationMode.watch([]
            {
                if (!Settings::VibrationMode)
                    stop_controller_rumble();
            });
        }

        bool apply() override
        {
            const int configuredId = int(Settings::VibrationControllerId);
            const int safeId = std::clamp(configuredId, 0, 3);
            if (configuredId != safeId)
            {
                Settings::VibrationControllerId = safeId;
                spdlog::warn(
                    "VibrationControllerId={} is outside XInput's 0..3 range; clamped to {}",
                    configuredId, safeId);
            }
            VibrationUserId = safeId;

            SetVibrationHook = safetyhook::create_inline(
                reinterpret_cast<void*>(&SetVibration), SetVibration_dest);
            return !!SetVibrationHook;
        }

        static VibrationRoutingFix instance;
    };

    VibrationRoutingFix VibrationRoutingFix::instance;

    class WheelFFBFeelRetune : public Hook
    {
    public:
        std::string_view description() override
        {
            return "WheelFFBFeelRetune";
        }

        void declare_settings() override
        {
            Settings::WheelFFBFeelRevision.hidden(true);
        }

        bool apply() override
        {
            int revision = int(Settings::WheelFFBFeelRevision);
            bool changed = false;

            if (revision < 1)
            {
                // Baseline feel is universal. Preserve SAT/trail gains, reduce
                // the low-speed centre spring, make real surface roughness easier
                // to feel, suppress normal-cornering scrub buzz, and retain an
                // unmistakable but short gear-change thunk.
                Settings::WheelFFBSpringStrength = 0.22f;
                Settings::WheelFFBSpringSaturation = 0.55f;
                Settings::WheelFFBRoadTexture = 0.60f;
                Settings::WheelFFBTireSlip = 0.04f;
                Settings::WheelFFBGearShift = 0.60f;
                Settings::WheelFFBFeelRevision = 1;
                revision = 1;
                changed = true;
            }

            if (revision < 2)
            {
                // Road/slip tactile transport is standardized across wheel
                // models. Hardware Spring/Damper remain capability-driven.
                Settings::WheelFFBUsePeriodicEffects = false;
                Settings::WheelFFBFeelRevision = 2;
                revision = 2;
                changed = true;
            }

            if (revision < 3)
            {
                // Input-device matching is separate from force tuning. Keep the
                // old R3 clean-install compatibility here without changing the
                // SAT/road/damper model selected for any wheel.
                const std::string configured =
                    lower_copy(Settings::WheelFFBDeviceName.get().c_str());
                if (configured == "moza")
                    Settings::WheelFFBDeviceName = "R3 Racing Wheel";

                Settings::WheelFFBFeelRevision = 3;
                revision = 3;
                changed = true;
            }

            if (revision < 4)
            {
                // v0.2 response retune for every wheel. Only values still equal
                // to v0.1 defaults are migrated; manual tuning is kept.
                const auto migrate_default = [](auto& setting, float oldValue, float newValue)
                {
                    const float current = static_cast<float>(setting);
                    if (std::isfinite(current) &&
                        std::abs(current - oldValue) <= 0.0005f)
                        setting = newValue;
                };

                migrate_default(Settings::WheelFFBSlewRate, 0.06f, 0.12f);
                migrate_default(Settings::WheelFFBReversalReleaseRate, 0.12f, 0.30f);
                migrate_default(Settings::WheelFFBTrailResponseLead, 0.25f, 0.40f);
                migrate_default(Settings::WheelFFBSteeringWeight, 1.45f, 1.60f);
                migrate_default(Settings::WheelFFBMechanicalTrail, 0.25f, 0.30f);

                Settings::WheelFFBFeelRevision = 4;
                revision = 4;
                changed = true;
            }

            if (revision < 5)
            {
                // Old F11 presets used a different response envelope and could
                // undo v0.2 tuning. Migrate only their exact signatures; all
                // other manual values remain untouched.
                normalize_legacy_preset(false);
                Settings::WheelFFBUsePeriodicEffects = false;
                Settings::WheelFFBFeelRevision = 5;
                revision = 5;
                changed = true;
            }

            if (!changed)
                return true;

            WheelFFB_ResetHeadroomStats();
            WheelFFB_RequestSettingsTransition();

            if (!Settings::write(Module::UserIniPath))
            {
                spdlog::warn(
                    "WheelFFBFeelRetune: applied revision {} for this session but could not persist user.ini",
                    revision);
            }
            else if (revision >= 5)
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 5 (device-independent v0.2 SAT/tactile defaults and legacy-preset migration)");
            }
            else if (revision >= 4)
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 4 (universal v0.2 SAT response: slew=0.12 reversal=0.30 trailLead=0.40 steeringWeight=1.60 mechanicalTrail=0.30 when still at v0.1 defaults)");
            }
            else if (revision >= 3)
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 3 (input-device compatibility migration; force tuning remains universal)");
            }
            else if (revision >= 2)
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 2 (spring=0.22 sat=0.55 road=0.60 tire-slip=0.04 gear=0.60, universal ConstantForce tactile path)");
            }
            else
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 1 (spring=0.22 sat=0.55 road=0.60 tire-slip=0.04 gear=0.60)");
            }
            return true;
        }

        static WheelFFBFeelRetune instance;
    };

    WheelFFBFeelRetune WheelFFBFeelRetune::instance;

    class WheelSelectorDPadAlias : public Hook
    {
        inline static SafetyHookInline InputUpdateHook = {};

        static void InputManager_Update_dest()
        {
            InputUpdateHook.ccall<void>();

            if (!Settings::UseNewInput || !Game::current_mode ||
                *Game::current_mode == STATE_GAME)
                return;

            auto& manager = InputManager::instance;
            const bool left = manager.actionFor(
                InputManager::ActionKind::Switch,
                int(SwitchId::SelectionLeft)).getState().isPressed();
            const bool right = manager.actionFor(
                InputManager::ActionKind::Switch,
                int(SwitchId::SelectionRight)).getState().isPressed();

            if (left == right)
                return;

            auto& steeringAction = manager.actionFor(
                InputManager::ActionKind::Volume,
                int(ADChannel::Steering));
            InputState steering = steeringAction.getState();

            // Real wheel motion wins. The alias exists only for front-end
            // selectors (car/BGM/etc.) which incorrectly ask the analogue
            // steering channel instead of SelectionLeft/SelectionRight.
            if (std::abs(steering.currentValue) >= 0.20f)
                return;

            steering.previousValue = steering.currentValue;
            steering.currentValue = left ? -1.0f : 1.0f;
            steering.isAxis = false;
            steering.lastSourceType = InputSourceType::GamePad;
            steeringAction.setState(steering);
        }

    public:
        std::string_view description() override
        {
            return "WheelSelectorDPadAlias";
        }

        bool apply() override
        {
            InputUpdateHook = safetyhook::create_inline(
                reinterpret_cast<void*>(&InputManager_Update), InputManager_Update_dest);
            return !!InputUpdateHook;
        }

        static WheelSelectorDPadAlias instance;
    };

    WheelSelectorDPadAlias WheelSelectorDPadAlias::instance;

    class WheelQuickSetupRemoval : public Hook
    {
        inline static SafetyHookInline ButtonHook = {};
        inline static SafetyHookInline SliderFloatHook = {};

        static bool __cdecl Button_dest(const char* label, const ImVec2& size)
        {
            if (label && std::strcmp(label, "Quick Setup") == 0)
            {
                // Keep the following SameLine() in Input Bindings well-defined
                // without leaving a clickable control or entering the separate
                // Quick Setup modal/state machine.
                ImGui::Dummy(ImVec2(0.0f, 0.0f));
                return false;
            }

            // The old UI implementation names these presets after R3 and writes
            // obsolete v0.1 values. Draw universal labels here and apply the
            // device-independent v0.2 preset directly; returning false prevents
            // the old caller block from overwriting the new values afterwards.
            if (label && std::strcmp(label, "Load MOZA R3 Physics SAT") == 0)
            {
                const bool clicked = ButtonHook.ccall<bool>(
                    "Load Universal Physics SAT", &size);
                if (clicked)
                {
                    apply_universal_physics_preset();
                    Settings::WheelFFBFeelRevision = 5;
                    WheelFFB_ResetHeadroomStats();
                    WheelFFB_RequestSettingsTransition();
                    if (!Settings::write(Module::UserIniPath))
                        spdlog::warn("WheelFFB: Universal Physics SAT preset active but user.ini could not be saved");
                }
                return false;
            }

            if (label && std::strcmp(label, "Load MOZA R3 Natural SAT") == 0)
            {
                const bool clicked = ButtonHook.ccall<bool>(
                    "Load Universal Natural SAT", &size);
                if (clicked)
                {
                    apply_universal_natural_preset();
                    Settings::WheelFFBFeelRevision = 5;
                    WheelFFB_ResetHeadroomStats();
                    WheelFFB_RequestSettingsTransition();
                    if (!Settings::write(Module::UserIniPath))
                        spdlog::warn("WheelFFB: Universal Natural SAT preset active but user.ini could not be saved");
                }
                return false;
            }

            // MSVC x86 passes a C++ reference as its underlying pointer. Passing
            // &size preserves ImGui::Button(const char*, const ImVec2&) exactly
            // through SafetyHook's cdecl trampoline.
            return ButtonHook.ccall<bool>(label, &size);
        }

        static bool __cdecl SliderFloat_dest(
            const char* label,
            float* value,
            float minimum,
            float maximum,
            const char* format,
            ImGuiSliderFlags flags)
        {
            // RoadTexture has a real setting range of 0..1.0 and the universal
            // default is 0.60. The old F11 slider stopped at 0.50, which could
            // silently clamp the migrated value simply by touching the control.
            if (label && std::strcmp(label, "Road Detail") == 0)
                maximum = std::max(maximum, 1.0f);

            return SliderFloatHook.ccall<bool>(
                label, value, minimum, maximum, format, flags);
        }

    public:
        std::string_view description() override
        {
            return "WheelQuickSetupRemoval";
        }

        bool apply() override
        {
            ButtonHook = safetyhook::create_inline(
                reinterpret_cast<void*>(&ImGui::Button), Button_dest);
            SliderFloatHook = safetyhook::create_inline(
                reinterpret_cast<void*>(&ImGui::SliderFloat), SliderFloat_dest);
            return !!ButtonHook && !!SliderFloatHook;
        }

        static WheelQuickSetupRemoval instance;
    };

    WheelQuickSetupRemoval WheelQuickSetupRemoval::instance;
}
