#!/usr/bin/env python3
"""R26 Quest-style cockpit ownership guard. Static checks, NOT HMD validation."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
code=(root/"src/hooks_graphics.cpp").read_text(encoding="utf-8")
car=(root/"src/vr/game/driver_seat_car_space.hpp").read_text(encoding="utf-8")
body=code.split("static bool VRDriverSeatCameraPose(",1)[1].split(
    "// START includes cinematics",1)[0]
# 2026-10-22 matching Quest3 evidence superseded the car-origin HMD
# anchor: offsets apply to the native in-car camera (with optional car axes).
# Keep the confirmed last-valid pose hold and original render-camera restore.
required = (
    "const auto& nativePos = camera->cam_pos_F8;",
    "const auto& nativeLook = camera->look_pos_104;",
    "const OutRunVR::DriverSeatCamera::CarAxes axes{",
    "m._31, m._32, m._33",
    "m._21, m._22, m._23",
    "ComputeStableSeatPose(",
    "Settings::VRDriverSeatCarSpaceBasis",
    "{nativePos.x, nativePos.y, nativePos.z}",
    "{nativeLook.x, nativeLook.y, nativeLook.z}",
    "hasLastValidPose",
    "lastPosition",
    "lastLook",
    "newPos = lastPosition",
    "newLook = lastLook",
)
def check_native_camera_anchor(source: str) -> None:
    body = source.split("static bool VRDriverSeatCameraPose(", 1)[1].split(
        "// START includes cinematics", 1)[0]
    for token in required:
        assert token in body, token
    assert body.index("const auto& nativePos =") < body.index(
        "ComputeStableSeatPose(") < body.index("lastPosition = newPos;")
    for forbidden in (
        "ComputeCarAnchoredSeatPose(",
        "ComputeTranslatedCamera(",
        "VRDriverSeatCarSpaceBasis axes",
        "m._41, m._42, m._43",
    ):
        assert forbidden not in body, forbidden
    return body

check_native_camera_anchor(code)
for label, needle, bad in (
    ("absolute car-anchor regression", "ComputeStableSeatPose(", "ComputeCarAnchoredSeatPose("),
    ("native position removed", "const auto& nativePos = camera->cam_pos_F8;", "const auto& nativePos = player->matrix_B0._41;"),
    ("native look removed", "const auto& nativeLook = camera->look_pos_104;", "const auto& nativeLook = player->matrix_B0._31;"),
    ("last stable fallback removed", "newPos = lastPosition", "newPos = {};"),
    ("user car-basis setting ignored", "Settings::VRDriverSeatCarSpaceBasis", "false"),
):
    mutated = code.replace(needle, bad, 1)
    assert mutated != code, "missing cockpit negative fixture: " + label
    try:
        check_native_camera_anchor(mutated)
    except (AssertionError, IndexError, ValueError):
        continue
    raise AssertionError("cockpit native-anchor mutation escaped: " + label)
for token in (
    "inline bool ComputeCarAnchoredSeatPose(",
    "inline bool ComputeStableSeatPose(",
):
    # The old helper is available for diagnostics, but intentionally NOT the
    # default active cockpit projection under the user-tested native anchor.
    assert token in (car + (root/"src/vr/game/driver_seat_camera_math.hpp").read_text(encoding="utf-8")), token
eligible=code.split("static bool VRDriverSeatCameraEligible(",1)[1].split(
    "class VRDriverSeatRenderTest",1)[0]
assert "PersistentDriverSeatSessionEligible(" in eligible
for forbidden in ("cam_mode_timer_364","cam_mode_34A","word340","word344",
                  "VRDriverSeatNativeMode","StableNativeViewEligible("):
    assert forbidden not in eligible, forbidden
assert "camera->cam_pos_F8 = savedPos;" in code
assert "camera->look_pos_104 = savedLook;" in code
ini=(root/"OutRun2006Tweaks.ini").read_text(encoding="utf-8")
settings=(root/"src/vr/settings.cpp").read_text(encoding="utf-8")
import re
def stock_vehicle_scale(config: str) -> bool:
    return len(re.findall(r"(?m)^\s*DriverSeatVehicleScale\s*=\s*1\.0+\s*$", config)) == 1
assert stock_vehicle_scale(ini), "shipped cockpit scale must be stock"
assert not stock_vehicle_scale(ini.replace("DriverSeatVehicleScale = 1.00",
                                      "DriverSeatVehicleScale = 1.15", 1))
assert '"DriverSeatVehicleScale", 1.0f' in settings
print("PASS Quest-style car-owned cockpit anchor + last-valid hold + source camera restore; HMD untested")