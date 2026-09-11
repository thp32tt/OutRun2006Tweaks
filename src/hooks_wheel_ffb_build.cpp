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
        Range<int>{ 0, 2 }
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

    float sample_max_surface_roughness(EVWORK_CAR* car)
    {
        if (!car)
            return 0.0f;

        float roughness = 0.0f;
        DWORD waterFlag = 0;
        for (int i = 0; i < 4; ++i)
        {
            const float surfaceRoughness = static_cast<float>(sub_1149C0(
                car->water_flag_24C[i],
                static_cast<int>(car->OnRoadPlace_5C.loadColiType_0),
                &waterFlag));
            if (std::isfinite(surfaceRoughness))
                roughness = std::max(roughness, surfaceRoughness);
        }
        return roughness;
    }
}

// MOZA R3 reports GUID_Sine creation/update support successfully, but real
// hardware testing shows that its road-texture sine can be effectively
// inaudible at the wheel. The engine already has a headroom-limited
// ConstantForce vibration fallback, so make that the reliable R3 path.
//
// Snow/Ice has a separate 4% attenuation in the production engine to avoid a
// constant DD-wheel buzz from the material baseline. Preserve a subtle 20%
// baseline there, but cancel that attenuation when the game's own per-wheel
// roughness rises above 0.55 (curb, shoulder, rough surface). Because the
// engine takes the maximum of all four wheel samples, one or two wheels are
// enough to trigger the tactile response.
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
    bool restoreRoadTexture = false;

    if (r3Compatibility && car && is_snow_or_ice_stage_for_ffb())
    {
        const float roughness = sample_max_surface_roughness(car);

        // hooks_wheel_ffb.cpp multiplies Snow/Ice RoadTexture by 0.04. A factor
        // of 25 therefore restores the normal surface amplitude. Leave the
        // ordinary snow/ice material at only 20% of normal (factor 5), while
        // letting a curb/shoulder roughness excursion use full tactile force.
        constexpr float CoreSnowScale = 0.04f;
        const float desiredRelativeScale = roughness > 0.55f ? 1.0f : 0.20f;
        Settings::WheelFFBRoadTexture =
            originalRoadTexture * (desiredRelativeScale / CoreSnowScale);
        restoreRoadTexture = true;
    }

    WheelFFB_UpdateAfterPhysics_Core(car);

    if (restoreRoadTexture)
        Settings::WheelFFBRoadTexture = originalRoadTexture;
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
                // through the already headroom-limited ConstantForce fallback.
                Settings::WheelFFBUsePeriodicEffects = false;
                Settings::WheelFFBFeelRevision = 2;
                revision = 2;
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
