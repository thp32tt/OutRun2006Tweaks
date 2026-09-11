from pathlib import Path
import subprocess


def read(path):
    return Path(path).read_text(encoding='utf-8')


def write(path, text):
    Path(path).write_text(text, encoding='utf-8')


def replace_once(path, old, new):
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one match, got {count}: {old[:120]!r}')
    write(path, text.replace(old, new, 1))


# Review pass 1: a live FFB disable is a full ownership release, not merely a
# zero-force state. This restores the driver's autocenter property and makes a
# later re-enable perform a clean DirectInput initialization.
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''            if (!Settings::WheelFFBEnable)\n            {\n                if (initialized_ && enabledLastTick_)\n                {\n                    zero_all_forces();\n                    reset_signal_state();\n                    enabledLastTick_ = false;\n                    spdlog::info("WheelFFB: disabled live; all effects zeroed immediately");\n                }\n                return;\n            }\n            enabledLastTick_ = true;\n''',
    '''            if (disable_live_if_needed())\n                return;\n            enabledLastTick_ = true;\n''')

replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''        void service_safety()\n        {\n            if (!initialized_ || panicStopped_) return;\n            const bool gameplay = Game::current_mode && *Game::current_mode == STATE_GAME;\n            const bool foreground = gameHwnd_ && GetForegroundWindow() == gameHwnd_;\n            if (!Settings::WheelFFBEnable || !gameplay || !foreground ||\n                ((Overlay::IsActive || Overlay::IsBindingDialogActive) && manualTestFrames_ == 0))\n            {\n                zero_all_forces();\n                reset_signal_state();\n                if ((!gameplay || !foreground || !Settings::WheelFFBEnable) && device_ && deviceAcquired_)\n                {\n                    device_->Unacquire();\n                    deviceAcquired_ = false;\n                }\n            }\n        }\n''',
    '''        void service_safety()\n        {\n            if (panicStopped_) return;\n            if (disable_live_if_needed()) return;\n            if (!initialized_) return;\n\n            const bool gameplay = Game::current_mode && *Game::current_mode == STATE_GAME;\n            const bool foreground = gameHwnd_ && GetForegroundWindow() == gameHwnd_;\n            if (!gameplay || !foreground ||\n                ((Overlay::IsActive || Overlay::IsBindingDialogActive) && manualTestFrames_ == 0))\n            {\n                zero_all_forces();\n                reset_signal_state();\n                if ((!gameplay || !foreground) && device_ && deviceAcquired_)\n                {\n                    device_->Unacquire();\n                    deviceAcquired_ = false;\n                }\n            }\n        }\n''')

replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''        bool output_owner_active() const\n        {\n            return Settings::WheelFFBEnable && initialized_ && device_ && !panicStopped_;\n        }\n''',
    '''        bool output_owner_active() const\n        {\n            return Settings::WheelFFBEnable && initialized_ && device_ &&\n                deviceAcquired_ && !deviceReinitPending_ && !panicStopped_;\n        }\n''')

replace_once(
    'src/hooks_wheel_ffb.cpp',
    '        void teardown_for_reinitialize()\n',
    '        void teardown_for_reinitialize(const char* autocenterReason = "device reinitialize")\n')
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '            restore_driver_autocenter("device reinitialize");\n',
    '            restore_driver_autocenter(autocenterReason);\n')

replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''        void clear_device_failure()\n        {\n            deviceFailureSince_ = 0;\n        }\n''',
    '''        bool disable_live_if_needed()\n        {\n            if (Settings::WheelFFBEnable)\n                return false;\n\n            const bool hadInitializedOutput = initialized_;\n            if (initialized_)\n            {\n                if (device_ && deviceAcquired_)\n                    zero_all_forces();\n                teardown_for_reinitialize("live disable");\n                initialized_ = false;\n                deviceReinitPending_ = false;\n                deviceFailureSince_ = 0;\n                deviceReinitAfter_ = 0;\n                retryAfter_ = 0;\n                failedInterfaceGuid_.clear();\n                failedInterfaceUntil_ = 0;\n            }\n\n            enabledLastTick_ = false;\n            if (hadInitializedOutput)\n                spdlog::info("WheelFFB: disabled live; output released and driver autocenter restored");\n            return true;\n        }\n\n        void clear_device_failure()\n        {\n            deviceFailureSince_ = 0;\n        }\n''')

# Review pass 2: Universal legacy ownership is already runtime-gated by
# WheelUniversalSetupEnable. Do not permanently erase the user's R3 helper
# preferences merely because Universal ownership is enabled temporarily.
replace_once(
    'src/overlay/wheel_setup_ui.cpp',
    '''            if (ImGui::Checkbox("Enable F11 universal wheel profile", Settings::WheelUniversalSetupEnable.ptr()))\n            {\n                if (Settings::WheelUniversalSetupEnable)\n                {\n                    // The old R3-specific readers assume fixed button numbers.\n                    // Once a universal profile is active, its own bindings must\n                    // be the sole wheel-menu source so Logitech/Thrustmaster/\n                    // Fanatec/Simagic/etc. do not inherit R3 button mappings.\n                    Settings::WheelMenuR3DirectDPad = false;\n                    Settings::WheelMenuR3DirectAB = false;\n                    status_ = "Universal profile enabled; legacy R3 fixed-button menu helpers were disabled.";\n                }\n            }\n''',
    '''            if (ImGui::Checkbox("Enable F11 universal wheel profile", Settings::WheelUniversalSetupEnable.ptr()))\n            {\n                status_ = Settings::WheelUniversalSetupEnable\n                    ? "Universal profile owns legacy menu input while enabled; configured R3 helpers remain saved and dormant."\n                    : "Universal profile disabled; configured legacy R3 helpers can resume automatically.";\n            }\n''')

replace_once(
    'src/overlay/wheel_setup_ui.cpp',
    '''                if (UniversalWheelProfile::copy_current_mapping())\n                {\n                    Settings::WheelUniversalSetupEnable = true;\n                    Settings::WheelMenuR3DirectDPad = false;\n                    Settings::WheelMenuR3DirectAB = false;\n                    status_ = "Imported current steering/pedal/shift bindings. Universal menu ownership enabled; add menu bindings below.";\n                }\n''',
    '''                if (UniversalWheelProfile::copy_current_mapping())\n                {\n                    Settings::WheelUniversalSetupEnable = true;\n                    status_ = "Imported current steering/pedal/shift bindings. Universal menu ownership enabled; saved R3 helpers remain dormant until Universal is disabled.";\n                }\n''')

# Review pass 3: the engine already detects a selected FFB GUID change and
# reinitializes the DirectInput output. Do not tell the user a restart is needed.
replace_once(
    'src/overlay/wheel_setup_ui.cpp',
    '                status_ = "Selected FFB output and saved its exact DirectInput GUID. Restart after changing the physical wheel base.";\n',
    '                status_ = "Selected FFB output and saved its exact DirectInput GUID. The FFB engine will reinitialize automatically on the next gameplay update.";\n')

replace_once(
    'src/hooks_forcefeedback.cpp',
    '''    // Suppress the independent gamepad-rumble path only after the\n    // DirectInput WheelFFBEngine has actually initialized an output device.\n    // A configured-but-missing/failed wheel must not disable controller rumble.\n''',
    '''    // Suppress the independent gamepad-rumble path only while the\n    // DirectInput WheelFFBEngine currently owns an acquired output device.\n    // A configured-but-missing/lost/unacquired wheel must not disable controller rumble.\n''')

# Review pass 5: make the source-only verifier protect the lifecycle/UI fixes.
verify = 'tools/verify_wheel_ffb_current.py'
replace_once(
    verify,
    "req(ffb, 'bool WheelFFB_IsOutputOwnerActive()', 'FFB ownership query exported')\n",
    "req(ffb, 'bool WheelFFB_IsOutputOwnerActive()', 'FFB ownership query exported')\n"
    "req(ffb, 'deviceAcquired_ && !deviceReinitPending_ && !panicStopped_', 'FFB ownership requires acquired healthy output')\n"
    "req(ffb, 'teardown_for_reinitialize(\"live disable\")', 'live FFB disable fully releases output')\n")

replace_once(
    verify,
    "req(r3_ab, '!Settings::UseNewInput &&\\n                Settings::WheelMenuR3DirectAB;', 'R3 AB hook can remain dormant under universal ownership')\n",
    "req(r3_ab, '!Settings::UseNewInput &&\\n                Settings::WheelMenuR3DirectAB;', 'R3 AB hook can remain dormant under universal ownership')\n"
    "forbid(wheel_ui, 'Settings::WheelMenuR3DirectDPad = false;', 'universal toggle preserves R3 DPad preference')\n"
    "forbid(wheel_ui, 'Settings::WheelMenuR3DirectAB = false;', 'universal toggle preserves R3 AB preference')\n"
    "forbid(wheel_ui, 'Restart after changing the physical wheel base', 'FFB selector does not demand unnecessary restart')\n")

# Source-only validation only. Do not run CMake, a compiler, or the numeric
# compiled test during the daytime review cycle.
subprocess.run(['python3', 'tools/verify_wheel_ffb_current.py'], check=True)
