#!/usr/bin/env python3
"""Native Quest D3D9Ex eye source + independent logical 2D UI regression.

This proves source policy and pure coordinate geometry only; HMD runtime remains
UNTESTED until the user checks menus/HUD with Quest 3.
"""
from pathlib import Path
from math import isclose

root = Path(__file__).resolve().parents[1]
settings = (root / "src/vr/settings.cpp").read_text()
upgrade = (root / "src/vr/d3d9/ex_device_upgrade.cpp").read_text()
ui = (root / "src/hooks_uiscaling.cpp").read_text()
renderer = (root / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text()
gfx = (root / "src/hooks_graphics.cpp").read_text()
launcher = (root / "tools/Run-FocusOfficialTest.ps1").read_text()
ini = (root / "OutRun2006Tweaks.ini").read_text()

def require(text, source, label):
    if text not in source:
        raise SystemExit("Missing " + label + ": " + text)

require('VRPreserveLogicalBackBuffer{ "VR", "PreserveLogicalBackBuffer", false,',
        settings, "native Quest source as default")
require('Settings::VRPreserveLogicalBackBuffer ||',
        upgrade, "reversible device-create fallback")
for token in (
    "'-PreserveLogicalBackBuffer=false'",
    "'-SkyGlowFactor=0'",
    "'-DisableSkyGlow=true'",
    "'-MirrorPreserveAspect=false'",
    "'-HudLogicalWidth=1920'",
    "'-HudLogicalHeight=1080'",
):
    require(token, launcher, "launcher policy")
for token in (
    "PreserveLogicalBackBuffer = false",
    "DisableSkyGlow = true",
    "MirrorPreserveAspect = false",
    "HudLogicalWidth = 1920",
    "HudLogicalHeight = 1080",
):
    require(token, ini, "packaged INI policy")
require("R30SkyGlowWanted() noexcept", renderer, "VR-only stereo glow bypass")
require("Settings::VREnabled && Settings::VRDisableSkyGlow", renderer,
        "VR-only scope; preserve 2D glow")
for token in ("Settings::VRHudLogicalWidth.get()",
              "Settings::VRHudLogicalHeight.get()"):
    require(token, renderer, "physical-eye independent HUD reference")
for token in ("Game::screen_resolution->x",
              "Game::screen_resolution->y",
              "OutRunVR::LogicalUI::Contain(",
              "CorroboratesHud(semantic)",
              "CorroboratesScreenOverlay2D(semantic)",
              "vp.Width >= 640 && vp.Height >= 480",
              "pOut->_41 = pOut->_41 * map.scale + map.x;",
              "pOut->_42 = pOut->_42 * map.scale + map.y;"):
    require(token, ui, "physical UI affine mapping")
require("if (Settings::VRMirrorPreserveAspect)", gfx,
        "reversible aspect-fitting mirror")

def contain(w, h, lw, lh):
    factor = min(w / lw, h / lh)
    return (factor, (w - lw * factor) * 0.5, (h - lh * factor) * 0.5)

# Quest eye 2496x2688 / logical HUD 1920x1080:
s, x, y = contain(2496, 2688, 1920, 1080)
assert isclose(s, 1.3) and isclose(x, 0) and isclose(y, 642)
assert isclose(960*s+x, 1248) and isclose(540*s+y, 1344)
# 1080p fallback must remain precisely stable with no affine distortion.
assert contain(1920, 1080, 1920, 1080) == (1.0, 0.0, 0.0)
# Future recommended eye sizes must remain dynamic.
s, x, y = contain(2064, 2208, 1920, 1080)
assert isclose(s, 1.075) and isclose(x, 0) and isclose(y, 523.5)
print("Native Quest eye / logical 2D menu+HUD / disabled VR SkyGlow geometry PASS; runtime HMD UNTESTED")
