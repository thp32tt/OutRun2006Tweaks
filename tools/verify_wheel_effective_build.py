from pathlib import Path
import hashlib


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def require(path: str, needle: str, label: str) -> None:
    text = read(path)
    if needle not in text:
        raise SystemExit(f"VERIFY FAILED [{label}]: {needle!r} not found in {path}")
    print(f"VERIFY OK [{label}]")


def forbid(path: str, needle: str, label: str) -> None:
    text = read(path)
    if needle in text:
        raise SystemExit(f"VERIFY FAILED [{label}]: stale {needle!r} still present in {path}")
    print(f"VERIFY OK [{label}]")


def digest(path: str) -> None:
    data = Path(path).read_bytes()
    print(f"SHA256 {path} {hashlib.sha256(data).hexdigest()}")


# Effective FFB source after all build-time patches.
require("src/hooks_wheel_ffb.cpp", 'Setting<bool> WheelFFBUseHardwareDamper{', "GUID_Damper setting")
require("src/hooks_wheel_ffb.cpp", 'GUID_Damper, &effect, &damperEffect_', "GUID_Damper creation")
require("src/hooks_wheel_ffb.cpp", 'springStrategy_ = 1;', "spring persistent DIEP_START")
require("src/hooks_wheel_ffb.cpp", 'damperStrategy_ = 1;', "damper persistent DIEP_START")
require("src/hooks_wheel_ffb.cpp", 'int periodicStrategy_ = 1;', "periodic persistent DIEP_START")
require("src/hooks_wheel_ffb.cpp", 'bool deviceAcquired_ = false;', "DirectInput acquisition state")
require("src/hooks_wheel_ffb.cpp", 'if (device_ && !deviceAcquired_)', "menu/gameplay reacquire")
require("src/hooks_wheel_ffb.cpp", 'textureRoughness', "road baseline filtering")
forbid("src/hooks_wheel_ffb.cpp", 'Keep the current software damper for this first comparison build.', "no stale software-damper block")

# R3-specific legacy defaults proven by physical testing.
require("src/hooks_input.cpp", 'Setting<bool> WheelAccelerationInvert{ "Controls", "WheelAccelerationInvert", false,', "R3 accelerator default")
require("src/hooks_wheel_input_compat_v2.hpp", '"Controls", "WheelPedalSplitFix", false,', "separate-pedal default")
require("OutRun2006Tweaks.ini", 'WheelAccelerationInvert = false', "shipped accelerator INI")

# Universal profile must own menu input when enabled.
require("src/hooks_wheel_r3_menu_dpad.hpp", '!Settings::WheelUniversalSetupEnable &&', "universal excludes fixed R3 D-pad helper")
require("src/hooks_wheel_r3_menu_ab.hpp", '!Settings::WheelUniversalSetupEnable &&', "universal excludes fixed R3 A/B helper")
require("src/overlay/wheel_setup_ui.cpp", 'ImGui::SliderInt("Steering Deadzone", &deadzonePercent, 0, 20, "%d%%")', "0-percent wheel deadzone UI")
require("src/overlay/wheel_setup_ui.cpp", 'ImGui::SeparatorText("Simulation FFB")', "combined simulation FFB panel")

for path in (
    "src/hooks_wheel_ffb.cpp",
    "src/hooks_wheel_input_compat_v2.hpp",
    "src/hooks_wheel_r3_menu_dpad.hpp",
    "src/hooks_wheel_r3_menu_ab.hpp",
    "src/overlay/wheel_setup_ui.cpp",
    "OutRun2006Tweaks.ini",
):
    digest(path)

print("Wheel effective-build verification passed")
