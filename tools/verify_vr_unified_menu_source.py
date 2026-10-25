#!/usr/bin/env python3
"""Quest3 source split: XR render quality and 2D references have independent owners."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
cfg=(R/"src/hooks_misc.cpp").read_text()
ex=(R/"src/vr/d3d9/ex_device_upgrade.cpp").read_text()
ui=(R/"src/hooks_uiscaling.cpp").read_text()
hooks=(R/"src/overlay/hooks_overlay.cpp").read_text()
shell=(R/"src/overlay/overlay.cpp").read_text()
run=(R/"tools/Run-DX9ExFocusTest.ps1").read_text()
ini=(R/"OutRun2006Tweaks.ini").read_text()

for t in ("AutoRenderResolution = true","FollowGameResolution = false",
          "UnifiedEyeMenuSource = false","Hud1080pReference = true",
          "HudScale = 0.55"):
    assert t in ini,t
for t in ("'-AutoRenderResolution=true'","'-FollowGameResolution=false'",
          "'-UnifiedEyeMenuSource=false'","'-Hud1080pReference=true'",
          "'-HudScale=0.55'"):
    assert t in run,t

assert "physical D3D9Ex target will use live OpenXR eye extent at CreateDevice" in cfg
assert "Game::screen_resolution->x = static_cast<int>(xrSize.width)" not in ex
assert "Game::screen_resolution->y = static_cast<int>(xrSize.height)" not in ex
assert "VRHud1080pReference" in ui
assert "? 80.0f" in ui
assert "spacing = 80.0f * Game::screen_scale->x;" in ui
assert "const bool vrUiPresentation = Settings::VREnabled;" in hooks
assert "f11VisibleThisFrame && vrUiPresentation" in hooks
render=shell.split("void Overlay::render_shell()",1)[1].split("void Overlay::init()",1)[0]
assert "const bool externalVrShell = Settings::VREnabled &&" in render
assert "Game::is_vr_gameplay_presentation() || !Game::is_in_game()" in render

physical_pad=(1920-640*(1080/480))/2
assert physical_pad==240
assert physical_pad/(1920/640)==80
print("PASS XR physical target + 1920x1080 HUD/F11 logical reference split; HMD UNTESTED")
