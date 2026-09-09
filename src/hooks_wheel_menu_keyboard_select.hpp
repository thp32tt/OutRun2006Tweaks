#pragma once

#include <Windows.h>
#include <cstdint>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"

// Legacy-wheel menu Select helper.
// The original controller calibration screen can stop accepting normal keyboard
// input after a DirectInput wheel is selected.  Keep Enter available as the
// game's A/Select action independently of the user's wheel/button bindings so a
// completely unassigned controller profile can still be calibrated manually.
namespace Settings
{
    Setting<bool> WheelMenuKeyboardEnterSelect{
        "Controls", "WheelMenuKeyboardEnterSelect", true,
        "In legacy wheel mode, maps keyboard Enter to the game's A/Select menu action."
    };
}

namespace
{
    class WheelMenuKeyboardSelect : public Hook
    {
        inline static constexpr uint32_t RawAMask = 0x00000002u;
        inline static constexpr uint32_t ASwitchMask = 1u << int(SwitchId::A);

        inline static SafetyHookInline ReadIOHook = {};
        inline static SafetyHookInline SwitchNowHook = {};
        inline static SafetyHookInline SwitchOnHook = {};

        inline static bool enterCurrent = false;
        inline static bool enterPrevious = false;
        inline static bool logged = false;

        static bool activeInMenu()
        {
            return Settings::WheelInputCompatibility &&
                !Settings::UseNewInput &&
                Settings::WheelMenuKeyboardEnterSelect &&
                Game::current_mode &&
                *Game::current_mode != STATE_GAME;
        }

        static bool enterHeldNow()
        {
            return (GetAsyncKeyState(VK_RETURN) & 0x8000) != 0;
        }

        static int ReadIO_dest()
        {
            const int result = ReadIOHook.ccall<int>();

            enterPrevious = enterCurrent;
            enterCurrent = activeInMenu() && enterHeldNow();

            if (!activeInMenu() || !Game::dinput_state)
                return result;

            auto* state = Game::dinput_state;
            if (enterCurrent)
                state->buttons_4 |= RawAMask;

            if (enterCurrent && !enterPrevious)
                state->pressed_8 |= RawAMask;
            else if (!enterCurrent && enterPrevious)
                state->released_C |= RawAMask;

            return result;
        }

        static int SwitchNow_dest(uint32_t switches)
        {
            const int result = SwitchNowHook.ccall<int>(switches);
            if (result)
                return result;

            if (activeInMenu() && switches == ASwitchMask && enterHeldNow())
            {
                if (!logged)
                {
                    logged = true;
                    spdlog::info("WheelMenuKeyboardEnterSelect: Enter mapped to legacy A/Select menu action");
                }
                return 1;
            }
            return 0;
        }

        static int SwitchOn_dest(uint32_t switches)
        {
            const int result = SwitchOnHook.ccall<int>(switches);
            if (result)
                return result;

            if (activeInMenu() && switches == ASwitchMask && enterCurrent && !enterPrevious)
                return 1;
            return 0;
        }

    public:
        std::string_view description() override
        {
            return "WheelMenuKeyboardEnterSelect";
        }

        bool validate() override
        {
            return Settings::WheelInputCompatibility;
        }

        void declare_settings() override
        {
            Settings::WheelMenuKeyboardEnterSelect.needs_restart();
        }

        bool apply() override
        {
            ReadIOHook = safetyhook::create_inline(Module::exe_ptr(0x53BB0), ReadIO_dest);
            SwitchNowHook = safetyhook::create_inline(Module::exe_ptr(0x536C0), SwitchNow_dest);
            SwitchOnHook = safetyhook::create_inline(Module::exe_ptr(0x536F0), SwitchOn_dest);

            const bool ok = !!ReadIOHook && !!SwitchNowHook && !!SwitchOnHook;
            if (ok)
                spdlog::info("WheelMenuKeyboardEnterSelect: enabled");
            return ok;
        }

        static WheelMenuKeyboardSelect instance;
    };

    WheelMenuKeyboardSelect WheelMenuKeyboardSelect::instance;
}
