// Build shim for the experimental WheelFFB implementation.
// Keep NOMINMAX local to this translation unit so Windows min/max macros do not
// collide with std::min/std::max/std::clamp in the DirectInput FFB engine.
#define NOMINMAX

// The production FFB implementation is compiled through this shim. Rename its
// exported update entry point locally so the shim can put a very small R3
// compatibility layer around one physics tick without duplicating the engine.
#define WheelFFB_UpdateAfterPhysics WheelFFB_UpdateAfterPhysics_Core
#include "hooks_wheel_ffb.cpp"
#undef WheelFFB_UpdateAfterPhysics

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

// The legacy vibration path lives in hooks_forcefeedback.cpp, but this wheel
// build owns the modern input/FFB integration. Keep its controller routing safe
// without duplicating the large Xbox-derived vibration routine.
namespace Settings
{
    extern Setting<int> VibrationMode;
    extern Setting<int> VibrationControllerId;

    // One-shot migration marker for the September 2026 R3 feel retune. Keeping
    // this persisted and hidden means the requested tuning is applied once, but
    // later manual slider changes are never overwritten on subsequent launches.
    Setting<int> WheelFFBFeelRevision{
        "WheelFFB", "FeelRevision", 0,
        "Internal one-shot migration version for wheel FFB feel defaults.",
        Range<int>{ 0, 3 }
    };
}

extern int VibrationUserId;
void SetVibration(int userId, float leftMotor, float rightMotor);
void InputManager_StopVibration();
void InputManager_Update();

namespace
{
    bool r3_road_texture_compatibility_needed()
    {
        const std::string configured =
            lower_copy(Settings::WheelFFBDeviceName.get().c_str());
        return configured.find("r3") != std::string::npos ||
               configured.find("moza") != std::string::npos;
    }

    bool is_snow_or_ice_stage_for_ffb()
    {
        if (!Game::GetNowStageNum || !Game::GetStageUniqueNum)
            return false;

        const int stageNumber = Game::GetNowStageNum(8);
        const int uniqueStage = Game::GetStageUniqueNum(stageNumber);
        return uniqueStage == 4 || uniqueStage == 19 ||
               uniqueStage == 34 || uniqueStage == 49;
    }

    struct RoadSurfaceProfile
    {
        float minimum = 1.0f;
        float maximum = 0.0f;
        float spread = 0.0f;
        int validSamples = 0;
    };

    RoadSurfaceProfile sample_surface_profile(EVWORK_CAR* car)
    {
        RoadSurfaceProfile result{};
        if (!car)
            return result;

        DWORD waterFlag = 0;
        for (int i = 0; i < 4; ++i)
        {
            const float roughness = static_cast<float>(sub_1149C0(
                car->water_flag_24C[i],
                static_cast<int>(car->OnRoadPlace_5C.loadColiType_0),
                &waterFlag));
            if (!std::isfinite(roughness))
                continue;

            result.minimum = std::min(result.minimum, roughness);
            result.maximum = std::max(result.maximum, roughness);
            ++result.validSamples;
        }

        if (result.validSamples == 0)
        {
            result.minimum = 0.0f;
            return result;
        }

        result.spread = std::max(0.0f, result.maximum - result.minimum);
        return result;
    }

    DWORD lastRoadCompatibilityLogTick = 0;
}

// MOZA R3 reports GUID_Sine creation/update support successfully, but real
// hardware testing shows that its road-texture sine can be effectively
// inaudible at the wheel. The engine already has a ConstantForce vibration
// fallback, so make that the reliable R3 path.
//
// A second R3-specific issue appears under loaded cornering: the sustained SAT
// can consume most of the ConstantForce range, making a small symmetric texture
// ripple almost disappear. During a *real surface transition* only (one/two
// wheels on a curb/shoulder, or a genuinely rough material), temporarily unload
// SAT/damping and normalize RoadTexture to a clear tactile amplitude. This does
// not weaken ordinary cornering and does not make straight asphalt vibrate.
//
// Snow is special because its four-wheel baseline can itself be around 0.50.
// Looking only at max roughness therefore misses a curb whose contacted wheels
// become *less* rough than the snow. The min/max spread across all four wheels
// catches that mixed-surface case regardless of which material has the larger
// scalar value. Once every sampled wheel is on a genuinely rough surface
// (minimum >= 0.60), keep the same strong tactile profile instead of dropping
// back to the weaker uniform-road profile.
void __cdecl WheelFFB_UpdateAfterPhysics(EVWORK_CAR* car)
{
    const bool r3Compatibility = r3_road_texture_compatibility_needed();

    // Do this live as well as through the migration below so loading an older
    // FFB profile cannot silently put an R3 back onto a driver-reported but
    // physically ineffective GUID_Sine path.
    if (r3Compatibility && Settings::WheelFFBUsePeriodicEffects)
        Settings::WheelFFBUsePeriodicEffects = false;

    const float originalRoadTexture =
        static_cast<float>(Settings::WheelFFBRoadTexture);
    const float originalSteeringWeight =
        static_cast<float>(Settings::WheelFFBSteeringWeight);
    const float originalDamperStrength =
        static_cast<float>(Settings::WheelFFBDamperStrength);

    bool restoreTactileOverrides = false;

    if (r3Compatibility && car)
    {
        const RoadSurfaceProfile surface = sample_surface_profile(car);
        const bool mixedSurface =
            surface.validSamples >= 2 && surface.spread >= 0.08f;
        const bool genuinelyRough = surface.maximum >= 0.60f;
        const bool fullyRough =
            surface.validSamples >= 2 && surface.minimum >= 0.60f;
        const bool strongTactile = mixedSurface || fullyRough;
        const bool tactileSurface = mixedSurface || genuinelyRough;

        if (tactileSurface)
        {
            const float speedRaw = std::isfinite(car->field_1C4)
                ? car->field_1C4 : 0.0f;
            const float speedNorm = std::clamp(speedRaw / 2.0f, 0.0f, 1.0f);
            const float roadSpeedGate =
                std::clamp((speedNorm - 0.05f) / 0.20f, 0.0f, 1.0f);
            const float textureRoughness =
                std::clamp((surface.maximum - 0.30f) / 0.55f, 0.0f, 1.0f);
            const float outputStrength = std::clamp(
                static_cast<float>(Settings::WheelFFBGlobalStrength), 0.0f, 1.5f);
            const bool snowStage = is_snow_or_ice_stage_for_ffb();
            const float coreStageScale = snowStage ? 0.04f : 1.0f;

            // Half-on-curb mixed contact is already clearly perceptible on the
            // user's R3. Fully crossing onto the same rough surface must not
            // become weaker merely because all four samples now agree.
            const float desiredRoadAmp = strongTactile ? 0.30f : 0.22f;
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

            // Keep exactly the same SAT/damper relief when the car completes the
            // transition onto a fully rough curb/shoulder. Previously mixed=false
            // immediately weakened these values, which matched the reported
            // vibration disappearing as the remaining tyres crossed the edge.
            const float steeringScale = strongTactile ? 0.72f : 0.80f;
            const float damperScale = strongTactile ? 0.55f : 0.70f;
            Settings::WheelFFBSteeringWeight =
                originalSteeringWeight * steeringScale;
            Settings::WheelFFBDamperStrength =
                originalDamperStrength * damperScale;
            restoreTactileOverrides = true;

            const DWORD now = GetTickCount();
            if (Settings::WheelFFBDebugLog &&
                now - lastRoadCompatibilityLogTick >= 750)
            {
                lastRoadCompatibilityLogTick = now;
                spdlog::info(
                    "WheelFFB ROAD: min={:.2f} max={:.2f} spread={:.2f} mixed={} fullRough={} snow={} targetAmp={:.2f} roadSetting={:.2f} satScale={:.2f} damperScale={:.2f}",
                    surface.minimum, surface.maximum, surface.spread,
                    mixedSurface, fullyRough, snowStage, desiredRoadAmp,
                    static_cast<float>(Settings::WheelFFBRoadTexture),
                    steeringScale, damperScale);
            }
        }
    }

    WheelFFB_UpdateAfterPhysics_Core(car);

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
                // The previous hardware spring dominated the R3 even though the
                // physics SAT signal itself was healthy. Preserve SAT/trail gains,
                // reduce the low-speed centre spring, make real surface roughness
                // easier to feel when only part of the car touches dirt, suppress
                // the normal-cornering scrub sine that felt like an asphalt buzz,
                // and restore an unmistakable but short gear-change thunk.
                Settings::WheelFFBSpringStrength = 0.22f;
                Settings::WheelFFBSpringSaturation = 0.55f;
                Settings::WheelFFBRoadTexture = 0.60f;
                Settings::WheelFFBTireSlip = 0.04f;
                Settings::WheelFFBGearShift = 0.60f;
                Settings::WheelFFBFeelRevision = 1;
                revision = 1;
                changed = true;
            }

            if (revision < 2 && r3_road_texture_compatibility_needed())
            {
                // R3 accepts GUID_Sine calls but the user's hardware produces no
                // useful tactile output from them. Route road/slip vibration
                // through the ConstantForce fallback.
                Settings::WheelFFBUsePeriodicEffects = false;
                Settings::WheelFFBFeelRevision = 2;
                revision = 2;
                changed = true;
            }

            if (revision < 3)
            {
                // DirectInput exposes this R3 as "R3 Racing Wheel and Pedals"
                // (SDL may prepend "Gudsen"), so the old default substring
                // "MOZA" cannot match a clean install. Use the stable R3 product
                // substring; once initialized the core still pins the exact GUID.
                const std::string configured =
                    lower_copy(Settings::WheelFFBDeviceName.get().c_str());
                if (configured == "moza")
                    Settings::WheelFFBDeviceName = "R3 Racing Wheel";

                Settings::WheelFFBFeelRevision = 3;
                revision = 3;
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
            else if (revision >= 3)
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 3 (R3 DirectInput auto-match + mixed-surface curb tactile)");
            }
            else if (revision >= 2)
            {
                spdlog::info(
                    "WheelFFBFeelRetune: applied revision 2 (spring=0.22 sat=0.55 road=0.60 tire-slip=0.04 gear=0.60, R3 road tactile=ConstantForce)");
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

            // MSVC x86 passes a C++ reference as its underlying pointer. Passing
            // &size preserves ImGui::Button(const char*, const ImVec2&) exactly
            // through SafetyHook's cdecl trampoline.
            return ButtonHook.ccall<bool>(label, &size);
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
            return !!ButtonHook;
        }

        static WheelQuickSetupRemoval instance;
    };

    WheelQuickSetupRemoval WheelQuickSetupRemoval::instance;
}
