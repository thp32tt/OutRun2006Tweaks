#!/usr/bin/env python3
"""Protect released FFB v0.2's VR-side legacy gamepad routing.

This verifier covers the mutable VR bridge, never the immutable release FFB
engine. It performs one contract check plus targeted negative mutations.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/hooks_forcefeedback.cpp"


INPUT_SOURCE = ROOT / "src/input_manager.hpp"


def lifetime_violations(source: str) -> list[str]:
    """The FFB-to-SDL handoff must not race gamepad disconnect/shutdown."""
    try:
        rumble = source.split("void setVibration(WORD left, WORD right)", 1)[1].split("// Add sources to bindings", 1)[0]
        shutdown = source.split("void shutdown()", 1)[1].split("SDL_Gamepad* getPrimaryGamepad()", 1)[0]
        unplug = source.split("void onControllerRemoved(SDL_JoystickID instanceId)", 1)[1].split("public:", 1)[0]
    except IndexError:
        return ["missing SDL lifetime boundary"]
    lock = "std::lock_guard<std::mutex> lock(mtx);"
    failures: list[str] = []
    if rumble.count(lock) != 1 or "getPrimaryGamepad()" not in rumble or "SDL_RumbleGamepad(controller, left, right, 1000);" not in rumble or not (rumble.index(lock) < rumble.index("getPrimaryGamepad()") < rumble.index("SDL_RumbleGamepad(controller, left, right, 1000);")):
        failures.append("rumble must resolve and use its SDL handle under the same mutex")
    if shutdown.count(lock) != 1 or "SDL_CloseGamepad(controller);" not in shutdown or shutdown.index(lock) > shutdown.index("SDL_CloseGamepad(controller);"):
        failures.append("shutdown must close SDL handles under the rumble mutex")
    if unplug.count(lock) != 1 or "SDL_CloseGamepad(*it);" not in unplug or unplug.index(lock) > unplug.index("SDL_CloseGamepad(*it);"):
        failures.append("hot-unplug must close SDL handles under the rumble mutex")
    return failures




def hotplug_shutdown_violations(source: str) -> list[str]:
    """Late gamepad/joystick add callbacks must not outlive terminal shutdown."""
    try:
        pad = source.split("void onControllerAdded(SDL_JoystickID instanceId)", 1)[1].split("void onJoystickAdded(", 1)[0]
        joy = source.split("void onJoystickAdded(SDL_JoystickID instanceId)", 1)[1].split("static bool deviceMatchesBinding", 1)[0]
        close = source.split("void shutdown()", 1)[1].split("SDL_Gamepad* getPrimaryGamepad()", 1)[0]
    except IndexError:
        return ["missing hotplug/shutdown lifetime boundary"]
    failures: list[str] = []
    mutex = "std::lock_guard<std::mutex> lock(mtx);"
    guard = "if (shuttingDown)"
    if "bool shuttingDown = false;" not in source:
        failures.append("shutdown fence default state missing")
    for body, opening, label in (
        (pad, "SDL_OpenGamepad(instanceId);", "controller"),
        (joy, "SDL_OpenJoystick(instanceId);", "joystick"),
    ):
        if not all(token in body for token in (mutex, guard, opening)) or (
            all(token in body for token in (mutex, guard, opening)) and
            not (body.index(mutex) < body.index(guard) < body.index("return;", body.index(guard)) < body.index(opening))
        ):
            failures.append(label + " add must hold mutex and fence shutdown before open")
    fence = "shuttingDown = true;"
    closed_pad = "SDL_CloseGamepad(controller);"
    if not all(token in close for token in (mutex, fence, closed_pad)) or (
        all(token in close for token in (mutex, fence, closed_pad)) and
        not (close.index(mutex) < close.index(fence) < close.index(closed_pad))
    ):
        failures.append("terminal shutdown must fence adds before device close")
    return failures

def primary_handoff_violations(source: str) -> list[str]:
    """SDL timed rumble must stop before primary switch, unplug and shutdown."""
    try:
        handoff = source.split("void setPrimaryGamepad(int index)", 1)[1].split("void init(HWND hwnd);", 1)[0]
        removal = source.split("void onControllerRemoved(SDL_JoystickID instanceId)", 1)[1].split("public:", 1)[0]
        shutdown = source.split("void shutdown()", 1)[1].split("SDL_Gamepad* getPrimaryGamepad()", 1)[0]
    except IndexError:
        return ["missing primary pad lifecycle boundary"]
    errors: list[str] = []
    ordered = (
        "const int nextIndex = (index >= 0 && index < int(controllers.size())) ? index : -1;",
        "if (nextIndex != primaryControllerIndex)",
        "if (auto* previous = getPrimaryGamepad())",
        "SDL_RumbleGamepad(previous, 0, 0, 0);",
        "primaryControllerIndex = nextIndex;",
    )
    if any(s not in handoff for s in ordered) or (
        all(s in handoff for s in ordered) and
        [handoff.index(s) for s in ordered] != sorted(handoff.index(s) for s in ordered)
    ):
        errors.append("primary switch fails to stop previously selected pad")
    for section, stop, close, label in (
        (removal, "SDL_RumbleGamepad(*it, 0, 0, 0);", "SDL_CloseGamepad(*it);", "unplug"),
        (shutdown, "SDL_RumbleGamepad(controller, 0, 0, 0);", "SDL_CloseGamepad(controller);", "shutdown"),
    ):
        if stop not in section or close not in section or section.index(stop) > section.index(close):
            errors.append(label + " must stop rumble before SDL close")
    return errors


def violations(source: str) -> list[str]:
    errors: list[str] = []
    try:
        entry = source.split("static void GamePlCar_Ctrl_Hook(EVWORK_CAR* car)", 1)[1].split("public:", 1)[0]
        route = source.split("void SetVibration(int userId, float leftMotor, float rightMotor)", 1)[1].split('extern "C"', 1)[0]
    except IndexError:
        return ["missing vibration hook or routing function"]

    if "VibrationUserId = Settings::VibrationControllerId;" not in source:
        errors.append("configured legacy controller identity not latched")
    selected_slot = source.split("Setting<int> VibrationControllerId{", 1)[1].split("};", 1)[0]
    if "Range<int>{ 0, 3 }" not in selected_slot:
        errors.append("XInput controller ID must be one of ports 0-3")
    if entry.count("SetVibration(VibrationUserId, VibrationLeftMotor, VibrationRightMotor);") != 1:
        errors.append("physics hook bypasses configured legacy controller identity")
    expected_order = ("CalcVibrationValues(car);",
                      "SetVibration(VibrationUserId, VibrationLeftMotor, VibrationRightMotor);",
                      "GamePlCar_Ctrl.call(car);",
                      "WheelFFB_UpdateAfterPhysics(car);")
    if any(marker not in entry for marker in expected_order) or (
        all(marker in entry for marker in expected_order) and
        [entry.index(marker) for marker in expected_order] !=
        sorted(entry.index(marker) for marker in expected_order)
    ):
        errors.append("legacy timing or released FFB post-physics order changed")
    if "if (WheelFFB_IsOutputOwnerActive())" not in route:
        errors.append("wheel ownership must suppress separate rumble")
    if "if (!wheelOwnedLastCall)" not in route or "rumbleDisabledLastCall = false;" not in route:
        errors.append("wheel acquisition/loss stop transition missing")
    if route.count("XInputSetState(userId, &zero);") != 3:
        errors.append("wheel-owned, disabled and SDL-handoff stops must target selected port")
    if "static bool legacyXInputOutputActive = false;" not in route or route.count("legacyXInputOutputActive = false;") != 4:
        errors.append("legacy rumble state must reset after wheel, disable and SDL handoff")
    disabled = route.split("if (!Settings::VibrationMode)", 1)[1].split("rumbleDisabledLastCall = true;", 1)[0]
    if "if (legacyXInputOutputActive || !Settings::UseNewInput)" not in disabled or "XInputSetState(userId, &zero);" not in disabled:
        errors.append("disable must stop previously driven XInput even after SDL switch")
    handoff = "if (Settings::UseNewInput && legacyXInputOutputActive)"
    if handoff not in route or route.index(handoff) > route.index("InputManager_SetVibration(vib.wLeftMotorSpeed, vib.wRightMotorSpeed);"):
        errors.append("SDL transition must clear previous XInput before forwarding new rumble")
    if "legacyXInputOutputActive = true;" not in route or route.index("legacyXInputOutputActive = true;") < route.index("XInputSetState(userId, &vib);"):
        errors.append("legacy rumble output must be tracked after XInput send")
    if "if (!Settings::UseNewInput)\n\t{\n\t\tXInputSetState(userId, &vib);" not in route:
        errors.append("legacy XInput output must use selected controller")
    sdl_only = ("if (Settings::UseNewInput)\n    {\n"
                "        InputManager_SetVibration(vib.wLeftMotorSpeed, vib.wRightMotorSpeed);\n"
                "        sdlRumbleOutputActive = true;\n    }")
    if sdl_only not in route or route.count("InputManager_SetVibration(vib.wLeftMotorSpeed, vib.wRightMotorSpeed);") != 1:
        errors.append("SDL rumble must only run on the selected SDL input backend")
    if "else if (sdlRumbleOutputActive)\n    {\n" not in route or (
        "InputManager_StopVibration();\n        sdlRumbleOutputActive = false;\n    }" not in route
    ):
        errors.append("SDL-to-XInput handoff must cancel the previously timed SDL rumble")
    wheel = (route.split("if (WheelFFB_IsOutputOwnerActive())", 1)[1]
             .split("wheelOwnedLastCall = false;", 1)[0]
             if "if (WheelFFB_IsOutputOwnerActive())" in route else "")
    disabled_stop = route.split("if (!Settings::VibrationMode)", 1)[1].split("rumbleDisabledLastCall = true;", 1)[0]
    if "InputManager_StopVibration();\n            sdlRumbleOutputActive = false;" not in wheel or (
        "InputManager_StopVibration();\n            sdlRumbleOutputActive = false;" not in disabled_stop
    ):
        errors.append("wheel acquisition and disabled rumble must reset SDL ownership state")
    if "if (!Settings::VibrationMode)" not in route:
        errors.append("disabled-rumble transition lost")
    return errors


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    errors = violations(source)
    if errors:
        raise SystemExit("VR FFB ROUTING FAIL: " + "; ".join(errors))
    mutations = (
        ("SetVibration(VibrationUserId, VibrationLeftMotor, VibrationRightMotor);",
         "SetVibration(0, VibrationLeftMotor, VibrationRightMotor);"),
        ("XInputSetState(userId, &zero);", "XInputSetState(Settings::VibrationControllerId, &zero);"),
        ("if (WheelFFB_IsOutputOwnerActive())", "if (false)"),
        ("GamePlCar_Ctrl.call(car);", "/* game trampoline omitted */"),
        ("VibrationUserId = Settings::VibrationControllerId;", "VibrationUserId = 0;"),
        ("Range<int>{ 0, 3 }", "Range<int>{ 0, 4 }"),
        ("if (Settings::UseNewInput && legacyXInputOutputActive)", "if (false)"),
        ("if (legacyXInputOutputActive || !Settings::UseNewInput)", "if (legacyXInputOutputActive)"),
        ("if (Settings::UseNewInput)\n    {\n        InputManager_SetVibration(", "if (true)\n    {\n        InputManager_SetVibration("),
        ("else if (sdlRumbleOutputActive)", "else if (false)"),
        ("InputManager_StopVibration();\n        sdlRumbleOutputActive = false;", "sdlRumbleOutputActive = false;"),
        ("legacyXInputOutputActive = true;", "legacyXInputOutputActive = false;"),
        ("legacyXInputOutputActive = false;\n    }\n\n    void InputManager_SetVibration", "/* handoff state clear removed */\n    }\n\n    void InputManager_SetVibration"),
    )
    for before, after in mutations:
        if before not in source or not violations(source.replace(before, after, 1)):
            raise SystemExit("VR FFB ROUTING mutation escaped: " + before)
    source_input = INPUT_SOURCE.read_text(encoding="utf-8")
    if lifetime_violations(source_input):
        raise SystemExit("VR FFB SDL LIFETIME FAIL: " + "; ".join(lifetime_violations(source_input)))
    if primary_handoff_violations(source_input):
        raise SystemExit("VR FFB SDL HANDOFF FAIL: " + "; ".join(primary_handoff_violations(source_input)))

    hotplug_errors = hotplug_shutdown_violations(source_input)
    if hotplug_errors:
        raise SystemExit("VR FFB SDL HOTPLUG FAIL: " + "; ".join(hotplug_errors))
    # Negative controls: a missing pad gate, joystick gate, mutex, or shutdown fence.
    negative_hotplug = (
        ("if (shuttingDown)", "if (false)"),
        ("void onJoystickAdded(SDL_JoystickID instanceId)", "void onJoystickAdded_MUTATED(SDL_JoystickID instanceId)"),
        ("std::lock_guard<std::mutex> lock(mtx);", "/* missing pad-open mutex */"),
        ("shuttingDown = true;", "/* terminal shutdown fence removed */"),
    )
    for before, after in negative_hotplug:
        mutated = source_input.replace(before, after, 1)
        if mutated == source_input or not hotplug_shutdown_violations(mutated):
            raise SystemExit("VR FFB SDL HOTPLUG mutation escaped: " + before[:64])
    negative_handoffs = (
        ("SDL_RumbleGamepad(previous, 0, 0, 0);", "/* primary stop removed */"),
        ("SDL_RumbleGamepad(*it, 0, 0, 0);", "/* unplug stop removed */"),
        ("SDL_RumbleGamepad(controller, 0, 0, 0);\n\t\t\tSDL_CloseGamepad(controller);", "/* shutdown stop removed */\n\t\t\tSDL_CloseGamepad(controller);"),
        ("if (nextIndex != primaryControllerIndex)", "if (false)"),
    )
    for original, mutated in negative_handoffs:
        if source_input.count(original) != 1 or not primary_handoff_violations(source_input.replace(original, mutated, 1)):
            raise SystemExit("VR FFB SDL HANDOFF mutation escaped: " + original)
    negative_lifetimes = (
        ("std::lock_guard<std::mutex> lock(mtx);\n\t\tauto* controller = getPrimaryGamepad();",
         "auto* controller = getPrimaryGamepad();\n\t\tstd::lock_guard<std::mutex> lock(mtx);"),
        ("void shutdown()\n\t{\n\t\t// Serialize teardown with VR/FFB rumble and SDL hot-unplug.\n\t\tstd::lock_guard<std::mutex> lock(mtx);",
         "void shutdown()\n\t{\n\t\t// unsafe unlocked teardown"),
    )
    for original, mutated in negative_lifetimes:
        if source_input.count(original) != 1 or not lifetime_violations(source_input.replace(original, mutated, 1)):
            raise SystemExit("VR FFB SDL LIFETIME mutation escaped: " + original[:60])
    print(f"VR FFB ROUTING PASS: selected legacy ID, wheel handoff, FFB post-physics, "
          f"{len(mutations)} routing + {len(negative_lifetimes)} lifetime + "
          f"{len(negative_handoffs)} handoff negative mutations")


if __name__ == "__main__":
    main()
