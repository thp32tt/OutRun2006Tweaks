// Build shim for the experimental WheelFFB implementation.
// Keep NOMINMAX local to this translation unit so Windows min/max macros do not
// collide with std::min/std::max/std::clamp in the DirectInput FFB engine.
#define NOMINMAX
#include "hooks_wheel_ffb.cpp"
#include "hooks_wheel_input_compat_v2.hpp"
#include "hooks_wheel_r3_menu_dpad.hpp"
#include "hooks_wheel_r3_menu_ab.hpp"
#include "hooks_wheel_r3_device_autoselect.hpp"
#include "hooks_wheel_menu_keyboard_back.hpp"
#include "hooks_wheel_menu_keyboard_select.hpp"
#include "hooks_wheel_legacy_blank_defaults.hpp"

// The legacy vibration path lives in hooks_forcefeedback.cpp, but this wheel
// build owns the modern input/FFB integration. Keep its controller routing safe
// without duplicating the large Xbox-derived vibration routine.
namespace Settings
{
    extern Setting<int> VibrationMode;
    extern Setting<int> VibrationControllerId;
}

extern int VibrationUserId;
void SetVibration(int userId, float leftMotor, float rightMotor);
void InputManager_StopVibration();

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
}
