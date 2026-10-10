#!/usr/bin/env python3
"""Protect released FFB v0.2's VR-side legacy gamepad routing.

This verifier covers the mutable VR bridge, never the immutable release FFB
engine. It performs one contract check plus targeted negative mutations.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/hooks_forcefeedback.cpp"


def violations(source: str) -> list[str]:
    errors: list[str] = []
    try:
        entry = source.split("static void GamePlCar_Ctrl_Hook(EVWORK_CAR* car)", 1)[1].split("public:", 1)[0]
        route = source.split("void SetVibration(int userId, float leftMotor, float rightMotor)", 1)[1].split('extern "C"', 1)[0]
    except IndexError:
        return ["missing vibration hook or routing function"]

    if "VibrationUserId = Settings::VibrationControllerId;" not in source:
        errors.append("configured legacy controller identity not latched")
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
    )
    for before, after in mutations:
        if before not in source or not violations(source.replace(before, after, 1)):
            raise SystemExit("VR FFB ROUTING mutation escaped: " + before)
    print(f"VR FFB ROUTING PASS: selected legacy ID, wheel handoff, FFB post-physics, {len(mutations)} negative mutations")


if __name__ == "__main__":
    main()
