from pathlib import Path

ffb_path = Path('src/hooks_wheel_ffb.cpp')
ui_path = Path('src/overlay/input_bindings_ui.cpp')
ini_path = Path('OutRun2006Tweaks.ini')

ffb = ffb_path.read_text(encoding='utf-8')
ui = ui_path.read_text(encoding='utf-8')
ini = ini_path.read_text(encoding='utf-8')


def rep(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, got {count}')
    print(f'cleanup patched: {label}')
    return text.replace(old, new, 1)


# 1) The multi-device binding screen still inherited the upstream gamepad reset
# value of 20%.  On a 270-degree wheel that is roughly +/-27 degrees around
# centre, so Reset to default must preserve the wheel-branch 0% baseline.
ui = rep(
    ui,
    'Settings::SteeringDeadZone = 0.2f;',
    'Settings::SteeringDeadZone = 0.0f;',
    'Reset to default keeps zero wheel deadzone')


# 2) The shipped values had already changed to the new multi-device input path,
# but the adjacent comments still told wheel users to leave UseNewInput false.
# Keep the documentation aligned with the actual hybrid architecture: SDL owns
# multi-device input, while the custom DirectInput COM engine remains the sole
# FFB owner. Legacy DirectInput remains an explicit fallback.
old_comment = '''# Enables new SDL-based input system\n# Allowing game to see full trigger range without any shared trigger axes issues\n# (experimental, not every menu/gamemode has been tested with it yet)\n# Leave false for steering wheels. WheelInputCompatibility also enforces this\n# after user.ini and command-line overrides are read.\nUseNewInput = true\n'''
new_comment = '''# Enables the multi-device SDL input system with raw joystick bindings.\n# This is the wheel-build default; force feedback remains on the custom\n# DirectInput COM engine. With an attached FFB wheel, automatic backend\n# selection prefers SDL DirectInput. Set false only when deliberately using\n# WheelInputCompatibility as the legacy input fallback.\nUseNewInput = true\n'''
ini = rep(ini, old_comment, new_comment, 'document the multi-device wheel default')


# 3) A direction-test button can be visible while the overlay is opened from a
# non-gameplay screen. Previously the request stayed queued and could fire on
# the first race frame. Reject such requests immediately, and also clear any
# pending test whenever the engine resets its gameplay signal state.
old_request = '''        void request_direction_test(int direction)\n        {\n            if (direction == 0)\n            {\n                manualTestFrames_ = 0;\n                if (initialized_ && !panicStopped_)\n                    set_constant_force(0);\n                return;\n            }\n            manualTestDirection_ = direction < 0 ? -1 : 1;\n            manualTestFrames_ = 18;\n            spdlog::info(\n                "WheelFFB: queued safe {} direction test at fixed 20% output",\n                manualTestDirection_ < 0 ? "left" : "right");\n        }\n'''
new_request = '''        void request_direction_test(int direction)\n        {\n            if (direction == 0)\n            {\n                manualTestFrames_ = 0;\n                manualTestDirection_ = 1;\n                if (initialized_ && !panicStopped_)\n                    set_constant_force(0);\n                return;\n            }\n\n            const bool inGameplay =\n                Game::current_mode && (*Game::current_mode == STATE_GAME);\n            if (!inGameplay)\n            {\n                manualTestFrames_ = 0;\n                manualTestDirection_ = 1;\n                spdlog::warn(\n                    "WheelFFB: ignored direction test outside gameplay; no torque was queued");\n                return;\n            }\n\n            manualTestDirection_ = direction < 0 ? -1 : 1;\n            manualTestFrames_ = 18;\n            spdlog::info(\n                "WheelFFB: queued safe {} direction test at fixed 20% output",\n                manualTestDirection_ < 0 ? "left" : "right");\n        }\n'''
ffb = rep(ffb, old_request, new_request, 'direction test is gameplay-only')

old_reset = '''            splashTimer_ = 0;\n            splashAmp_ = 0.0f;\n\n            // Menu/race transitions must not reuse samples from the previous\n'''
new_reset = '''            splashTimer_ = 0;\n            splashAmp_ = 0.0f;\n            manualTestFrames_ = 0;\n            manualTestDirection_ = 1;\n\n            // Menu/race transitions must not reuse samples from the previous\n'''
ffb = rep(ffb, old_reset, new_reset, 'signal reset clears pending direction test')

ffb_path.write_text(ffb, encoding='utf-8')
ui_path.write_text(ui, encoding='utf-8')
ini_path.write_text(ini, encoding='utf-8')
print('Applied final wheel cleanup: reset deadzone, input docs, direction-test safety')
