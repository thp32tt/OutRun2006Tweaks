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
    if route.count("XInputSetState(userId, &zero);") != 2:
        errors.append("wheel-owned and disabled stop must address same selected controller")
    if "if (!Settings::UseNewInput)\n\t\tXInputSetState(userId, &vib);" not in route:
        errors.append("legacy XInput output must use selected controller")
    if "InputManager_SetVibration(vib.wLeftMotorSpeed, vib.wRightMotorSpeed);" not in route:
        errors.append("SDL output forwarding lost")
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
    )
    for before, after in mutations:
        if before not in source or not violations(source.replace(before, after, 1)):
            raise SystemExit("VR FFB ROUTING mutation escaped: " + before)
    source_input = INPUT_SOURCE.read_text(encoding="utf-8")
    if lifetime_violations(source_input):
        raise SystemExit("VR FFB SDL LIFETIME FAIL: " + "; ".join(lifetime_violations(source_input)))
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
          f"{len(mutations)} routing + {len(negative_lifetimes)} lifetime negative mutations")


if __name__ == "__main__":
    main()
