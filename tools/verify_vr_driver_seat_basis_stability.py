#!/usr/bin/env python3
"""R26 Quest-style cockpit ownership guard. Static checks, NOT HMD validation."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
code=(root/"src/hooks_graphics.cpp").read_text(encoding="utf-8")
car=(root/"src/vr/game/driver_seat_car_space.hpp").read_text(encoding="utf-8")
body=code.split("static bool VRDriverSeatCameraPose(",1)[1].split(
    "// START includes cinematics",1)[0]
for token in (
    "ComputeCarAnchoredSeatPose(",
    "m._41, m._42, m._43",
    "m._31, m._32, m._33",
    "m._21, m._22, m._23",
    "hasLastValidPose",
    "lastPosition",
    "lastLook",
    "newPos = lastPosition",
    "newLook = lastLook",
):
    assert token in body, token
for forbidden in (
    "camera->cam_pos_F8",
    "camera->look_pos_104",
    "ComputeStableSeatPose(",
    "ComputeTranslatedCamera(",
    "VRDriverSeatCarSpaceBasis",
):
    assert forbidden not in body, forbidden
for token in (
    "inline bool ComputeCarAnchoredSeatPose(",
    "carOrigin",
    "cross(forward, seedUp)",
    "double(carOrigin.x)",
    "lookDistance",
):
    assert token in car, token
eligible=code.split("static bool VRDriverSeatCameraEligible(",1)[1].split(
    "class VRDriverSeatRenderTest",1)[0]
assert "PersistentDriverSeatSessionEligible(" in eligible
for forbidden in ("cam_mode_timer_364","cam_mode_34A","word340","word344",
                  "VRDriverSeatNativeMode","StableNativeViewEligible("):
    assert forbidden not in eligible, forbidden
assert "camera->cam_pos_F8 = savedPos;" in code
assert "camera->look_pos_104 = savedLook;" in code
print("PASS Quest-style car-owned cockpit anchor + last-valid hold + source camera restore; HMD untested")