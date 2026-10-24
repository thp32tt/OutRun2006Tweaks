#!/usr/bin/env python3
"""GOAL-completion and stock-camera acceptance on isolated R26 candidate; NOT HMD validation."""
from pathlib import Path
import re
root = Path(__file__).resolve().parents[1]
ui = (root / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
cam = (root / "src/hooks_graphics.cpp").read_text(encoding="utf-8")
settings = (root / "src/vr/settings.cpp").read_text(encoding="utf-8")
ini = (root / "OutRun2006Tweaks.ini").read_text(encoding="utf-8")
assert 'VRDriverSeatView{ "VR", "DriverSeatView", false,' in settings
assert re.search(r"(?m)^DriverSeatView\s*=\s*false\s*$", ini)
assert re.search(r"(?m)^DriverSeatGlassMaterialTrace\s*=\s*false\s*$", ini)
assert "if (!owner.armed || !nativeModeMatches)" in cam
assert "camera->cam_mode_timer_364 == 0" in cam
assert "camera->cam_pos_F8 = savedPos;" in cam
assert "camera->look_pos_104 = savedLook;" in cam
assert "StageExtensionAdmission = {" in ui
part = ui.split("static void StageExtensionEnter(", 1)[1].split("static void StageExtensionLeave(", 1)[0]
assert "*Game::current_mode == GameState::STATE_GOAL" in part
assert "Settings::VREnabled && goalSummary" in part
part = ui.split("static void StageExtensionLeave(", 1)[1].split("static void", 1)[0]
assert "*Game::current_mode == GameState::STATE_GOAL" in part
assert "VR GOAL POST_TABLE E8:" in part
assert "ResultTextB9200InlineHook.call<void>(text, x, y, step);" in ui
assert "Module::exe_ptr(0xB9200), ResultTextB9200_dest" in ui
assert "IsOriginalB9200ParentReturn(" in ui
assert "if (!exactGoalParent)" in ui
assert "FlushD3DXBeforeDirectGoalSource();" in ui
assert "FlushD3DXAtDirectGoalSourceExit();" in ui
assert "0x97C57 + 5" in ui and "rva+5 midhooks disabled" in ui
assert not re.search(r"safetyhook::create_mid\(\s*Module::exe_ptr\(0x97C5[BCDF]\)", ui)
assert "HudScale = 0.55" in ini
assert "CullingUnionMarginDegrees = 8.0" in ini
assert "UnifiedEyeMenuSource = false" in ini
assert "FollowGameResolution = true" in ini
section = ""
keys = set()
for raw in ini.splitlines():
    line = raw.strip()
    if not line or line.startswith(("#", ";")): continue
    if line.startswith("[") and line.endswith("]"):
        section = line.lower()
        continue
    if "=" in line:
        key = (section, line.split("=", 1)[0].strip().lower())
        assert key not in keys, f"duplicate INI key: {key}"
        keys.add(key)
print("PASS: GOAL post-table admission, safe B9200 entry, native camera mode, settings and unique INI")
