// Build shim for the experimental WheelFFB implementation.
// Keep NOMINMAX local to this translation unit so Windows min/max macros do not
// collide with std::min/std::max/std::clamp in the DirectInput FFB engine.
#define NOMINMAX

// Compile the core under a private update-entry alias so this shim can retain
// legacy preset migration/controller-rumble routing around it.
#define WheelFFB_UpdateAfterPhysics WheelFFB_UpdateAfterPhysics_Core
#include "hooks_wheel_ffb.cpp"
#undef WheelFFB_UpdateAfterPhysics

#include "input_manager.hpp"
#include "hooks_wheel_input_compat_v2.hpp"
#include "hooks_wheel_native_physics_research.hpp"
#include "hooks_wheel_r3_menu_dpad.hpp"
#include "hooks_wheel_r3_menu_ab.hpp"
#include "hooks_wheel_r3_device_autoselect.hpp"
#include "hooks_wheel_menu_keyboard_back.hpp"
#include "hooks_wheel_menu_keyboard_select.hpp"
#include "hooks_wheel_legacy_blank_defaults.hpp"

#include <imgui.h>
#include <cstring>

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
        Range<int>{ 0, 8 }
    };
}

extern int VibrationUserId;
void SetVibration(int userId, float leftMotor, float rightMotor);
void InputManager_StopVibration();
void InputManager_Update();

namespace
{
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
        Settings::WheelFFBFeedbackCharacter = 0;
        Settings::WheelFFBXForceMix = 0.50f;
        Settings::WheelFFBXForceInvert = false;
        Settings::WheelFFBXForceGain = 1.00f;
        Settings::WheelFFBNativeTireSat = false;
        Settings::WheelFFBNativeTireSatGain = 1.00f;
        Settings::WheelFFBNativeTireSatInvert = false;
        Settings::WheelFFBNativeOversteerCue = false;
        Settings::WheelFFBNativeOversteerStrength = 0.10f;
        Settings::WheelFFBNativeOversteerSlipThreshold = 0.12f;
        Settings::WheelFFBNativeOversteerInvert = false;
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
        Settings::WheelFFBRoadTexture = 0.30f;
        Settings::WheelFFBCurbImpact = 0.40f;
        Settings::WheelFFBTireSlip = 0.04f;
        Settings::WheelFFBWallImpact = 0.38f;
        Settings::WheelFFBGearShift = 0.60f;
        Settings::WheelFFBEngineVibration = false;
        Settings::WheelFFBEngineIdle = 0.20f;
        Settings::WheelFFBUseHardwareSpring = true;
        Settings::WheelFFBUseHardwareDamper = true;
        Settings::WheelFFBUsePeriodicEffects = false;
        Settings::WheelFFBInvertForce = false;
        Settings::WheelFFBInvertSpring = false;
        Settings::WheelFFBDebugLog = true;
        Settings::VibrationMode = 0;
    }

    void apply_universal_natural_preset()
    {
        Settings::WheelFFBEnable = true;
        Settings::WheelFFBPhysicsSat = false;
        Settings::WheelFFBFeedbackCharacter = 0;
        Settings::WheelFFBXForceMix = 0.50f;
        Settings::WheelFFBXForceInvert = false;
        Settings::WheelFFBXForceGain = 1.00f;
        Settings::WheelFFBNativeTireSat = false;
        Settings::WheelFFBNativeTireSatGain = 1.00f;
        Settings::WheelFFBNativeTireSatInvert = false;
        Settings::WheelFFBNativeOversteerCue = false;
        Settings::WheelFFBNativeOversteerStrength = 0.10f;
        Settings::WheelFFBNativeOversteerSlipThreshold = 0.12f;
        Settings::WheelFFBNativeOversteerInvert = false;
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
        Settings::WheelFFBRoadTexture = 0.30f;
        Settings::WheelFFBCurbImpact = 0.40f;
        Settings::WheelFFBTireSlip = 0.04f;
        Settings::WheelFFBWallImpact = 0.38f;
        Settings::WheelFFBGearShift = 0.60f;
        Settings::WheelFFBEngineVibration = false;
        Settings::WheelFFBEngineIdle = 0.20f;
        Settings::WheelFFBUseHardwareSpring = true;
        Settings::WheelFFBUseHardwareDamper = true;
        Settings::WheelFFBUsePeriodicEffects = false;
        Settings::WheelFFBInvertForce = false;
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

}

// The core now owns road/curb haptics directly from per-wheel material and
// suspension/load signals. This wrapper only keeps legacy preset migration,
// standardized ConstantForce tactile transport, and read-only research capture.
void __cdecl WheelFFB_UpdateAfterPhysics(EVWORK_CAR* car)
{
    normalize_legacy_preset(true);

    // Keep one tactile transport across wheels. The new road model itself no
    // longer depends on the old Xbox roughness LUT or snow-stage exceptions.
    if (Settings::WheelFFBUsePeriodicEffects)
        Settings::WheelFFBUsePeriodicEffects = false;

    WheelFFB_UpdateAfterPhysics_Core(car);
    WheelNativePhysicsResearch::capture_after_physics(car);
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
                // the low-speed centre spring, keep road texture conservative,
                // suppress normal-cornering scrub buzz, and retain an
                // unmistakable but short gear-change thunk.
                Settings::WheelFFBSpringStrength = 0.22f;
                Settings::WheelFFBSpringSaturation = 0.55f;
                Settings::WheelFFBRoadTexture = 0.30f;
                Settings::WheelFFBCurbImpact = 0.40f;
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

            if (revision < 6)
            {
                // v0.4 hardware validation found the original experimental rear
                // cue sign reversed. The production formula is now corrected,
                // so clear the old compatibility invert and soften only the old
                // 0.18 default; deliberate custom strength remains untouched.
                const float rearStrength =
                    static_cast<float>(Settings::WheelFFBNativeOversteerStrength);
                if (std::isfinite(rearStrength) &&
                    std::abs(rearStrength - 0.18f) <= 0.0005f)
                    Settings::WheelFFBNativeOversteerStrength = 0.10f;
                Settings::WheelFFBNativeOversteerInvert = false;
                Settings::WheelFFBFeelRevision = 6;
                revision = 6;
                changed = true;
            }

            if (revision < 7)
            {
                // Live R3 testing confirmed that the corrected internal Physics
                // SAT and rear-cue signs need no output inversion. Earlier R3
                // candidates often had both the global and native SAT Reverse
                // switches enabled, which double-inverted into an apparently
                // correct result. Normalize only the validated R3 device family;
                // preserve inversion choices for unknown wheel hardware.
                const std::string device =
                    lower_copy(Settings::WheelFFBDeviceName.get().c_str());
                const bool validatedR3 =
                    device.find("r3 racing wheel") != std::string::npos ||
                    device.find("moza r3") != std::string::npos;
                if (validatedR3)
                {
                    Settings::WheelFFBInvertForce = false;
                    Settings::WheelFFBNativeTireSatInvert = false;
                    Settings::WheelFFBNativeOversteerInvert = false;
                }
                Settings::WheelFFBFeelRevision = 7;
                revision = 7;
                changed = true;
            }

            if (revision < 8)
            {
                // v0.4 surface rewrite: the old 0.60 RoadTexture default was
                // tuned around max(Xbox roughness). The new per-wheel physical
                // model deliberately keeps continuous texture subtle and has a
                // separate bounded curb/bump pulse.
                const float road =
                    static_cast<float>(Settings::WheelFFBRoadTexture);
                if (std::isfinite(road) &&
                    std::abs(road - 0.60f) <= 0.0005f)
                    Settings::WheelFFBRoadTexture = 0.30f;
                Settings::WheelFFBCurbImpact = 0.40f;
                Settings::WheelFFBFeelRevision = 8;
                revision = 8;
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
            else if (revision >= 8)
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 8 (per-wheel material+suspension road model; max roughness and snow-stage hacks removed)");
            }
            else if (revision >= 7)
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 7 (R3 validated with global/native SAT reverse OFF; drift re-grip stabilization enabled in runtime)");
            }
            else if (revision >= 6)
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 6 (rear countersteer sign corrected; legacy 0.18 cue default softened to 0.10)");
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

            // Reuse this established input hook for diagnostic capture rather
            // than stacking another inline hook on InputManager_Update.
            if (Settings::UseNewInput)
                WheelXForceResearch::capture_neighbors();

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
                    Settings::WheelFFBFeelRevision = 8;
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
                    Settings::WheelFFBFeelRevision = 8;
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
