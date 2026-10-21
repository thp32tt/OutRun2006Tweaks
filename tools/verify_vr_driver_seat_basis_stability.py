#!/usr/bin/env python3
"""R26 cockpit camera oscillation guard. Static checks, NOT HMD validation."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
code=(root/"src/hooks_graphics.cpp").read_text(encoding="utf-8")
ini=(root/"OutRun2006Tweaks.ini").read_text(encoding="utf-8")
settings=(root/"src/vr/settings.cpp").read_text(encoding="utf-8")
body=code.split("static bool VRDriverSeatCameraPose(",1)[1].split(
    "// START includes cinematics",1)[0]
assert "DriverSeatCarSpaceBasis = false" in ini
assert '"DriverSeatCarSpaceBasis", false,' in settings
for token in (
    "carSpaceFallbackLatched",
    "mode != lastCameraMode",
    "camera != lastCamera",
    "!VRDriverSeatGameplayActive()",
    "Settings::VRDriverSeatCarSpaceBasis && !carSpaceFallbackLatched",
    "&usedCarSpace",
    "carSpaceRequested && !usedCarSpace",
    "carSpaceFallbackLatched = true;",
    "ComputeStableSeatPose(",
):
    assert token in body, token
assert body.index("const bool carSpaceRequested =") < body.index(
    "ComputeStableSeatPose(") < body.index(
    "if (carSpaceRequested && !usedCarSpace)")
assert "static bool VRDriverSeatGameplayActive() noexcept;" in code
eligible=code.split("static bool VRDriverSeatCameraEligible(",1)[1].split(
    "class VRDriverSeatRenderTest",1)[0]
assert "PersistentDriverSeatSessionEligible(" in eligible
for forbidden in (
    "cam_mode_timer_364",
    "cam_mode_34A",
    "word340",
    "word344",
    "VRDriverSeatNativeMode",
    "StableNativeViewEligible(",
    "NativeCameraModeEligible(",
):
    assert forbidden not in eligible, forbidden
assert "camera->cam_pos_F8 = savedPos;" in code
assert "camera->look_pos_104 = savedLook;" in code
# Deterministic simulated transitions for the new sticky native fallback.
latched=False
for car_basis_valid in (True,True,False,True,False,True):
    requested=not latched
    used=requested and car_basis_valid
    if requested and not used:
        latched=True
    if latched:
        assert not used
assert latched
# The live cockpit gate is intentionally independent of native camera
# transition state. Static source inspection above guards that contract.
print("PASS persistent cockpit session gate + basis fallback + source camera state restore; HMD untested")