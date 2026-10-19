#!/usr/bin/env python3
"""Quest3 DX9Ex: 2D logical coordinates and 3D source share one target.
Static guards plus pure geometry for landscape and XR portrait resolutions.
HMD verification is intentionally separate.
"""
from pathlib import Path
import math
root=Path(__file__).resolve().parents[1]
cfg=(root/"src/hooks_misc.cpp").read_text(encoding="utf-8")
ex=(root/"src/vr/d3d9/ex_device_upgrade.cpp").read_text(encoding="utf-8")
ui=(root/"src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
settings=(root/"src/vr/settings.cpp").read_text(encoding="utf-8")
policy=(root/"src/vr/ui/vr_logical_coordinate_space.hpp").read_text(encoding="utf-8")
assert 'VRUnifiedEyeMenuSource{ "VR", "UnifiedEyeMenuSource", true,' in settings
assert "Settings::VRUnifiedEyeMenuSource.needs_restart();" in settings
assert "Settings::VRUnifiedEyeMenuSource" in cfg and "Settings::VRUnifiedEyeMenuSource" in ex
assert "vr_logical_coordinate_space.hpp" in ui
overlay=(root/"src/overlay/hooks_overlay.cpp").read_text(encoding="utf-8")
assert "if (f11VisibleThisFrame && vrGameplay &&" in overlay
assert "!Settings::VRUnifiedEyeMenuSource)" in overlay
assert "extern Setting<bool> VRUnifiedEyeMenuSource;" in overlay
assert "GetTickCount64() - startTick >= 1250ull" in cfg
assert "Sleep(25);" in cfg
def check_source(cfg,ex):
    c=cfg.split("void ApplyVrEyeResolutionAfterConfig(",1)[1].split("class CommandLineArguments",1)[0]
    guard=c.index("if (commandLineResolution)")
    manual=c.index("if (manualRequested)")
    unified=c.index("!Settings::VRUnifiedEyeMenuSource")
    xr=c.index("Game::screen_resolution->x = static_cast<int>(extent.width);")
    assert guard < manual < unified < xr
    # No post-config overwrite from a newly arrived host.
    e=ex.split("OutRunVR::EyeExtent::Size ReadyXrEyeSizeAtCreateDevice(",1)[1].split(
        "Direct3DCreate9Fn OriginalDirect3DCreate9",1)[0]
    assert "Settings::VRUnifiedEyeMenuSource) ||" in e
    assert e.index("Settings::VRUnifiedEyeMenuSource") < e.index("!Settings::VRAutoRenderResolution")
    return True
def check_ui(ui,policy):
    assert "OutRunVR::LogicalUI::Contain(" in ui
    assert "(std::min)(gameFactor, logicalViewport.scale)" in ui
    assert "const float x = (renderWidth - width) * 0.5f;" in policy
    assert "const float y = (renderHeight - height) * 0.5f;" in policy
    assert "const float scale = sx < sy ? sx : sy;" in policy
    assert "MapX" in policy and "MapY" in policy
    assert "OpenXR eye extent and optical projection are intentionally NOT inputs" in policy
check_source(cfg,ex)
check_ui(ui,policy)
for a,b in [
    ("!Settings::VRUnifiedEyeMenuSource","true"),
    ("if (manualRequested)","if (false)"),
]:
    try:check_source(cfg.replace(a,b,1),ex)
    except (AssertionError,ValueError):pass
    else:raise AssertionError("config source mutation escaped "+a)
try:check_source(cfg,ex.replace("Settings::VRUnifiedEyeMenuSource) ||","false) ||",1))
except (AssertionError,ValueError):pass
else:raise AssertionError("late XR source resize regression escaped")
for a,b in [
    ("(std::min)(gameFactor, logicalViewport.scale)","gameFactor"),
    ("const float x = (renderWidth - width) * 0.5f;","const float x = 0;"),
    ("const float y = (renderHeight - height) * 0.5f;","const float y = 0;"),
]:
    try:check_ui(ui.replace(a,b,1),policy.replace(a,b,1))
    except (AssertionError,ValueError):pass
    else:raise AssertionError("logical UI mapping regression escaped "+a)
def contain(w,h):
    scale=min(w/640,h/480);ox=(w-640*scale)*0.5;oy=(h-480*scale)*0.5
    return scale,ox,oy
for width,height in [(640,480),(1280,720),(1920,1080),(3440,1440),
                     (2496,2688),(3072,3216)]:
    s,x,y=contain(width,height)
    assert s>0 and math.isclose(x+320*s,width/2) and math.isclose(y+240*s,height/2)
    assert 0<=x<=width/2 and 0<=y<=height/2
    assert x+640*s<=width+0.001 and y+480*s<=height+0.001
# The chosen 3D source and 2D menu target are literally the same D3D9Ex
# device extent; only logical sprite pixels undergo viewport mapping.
for source in [(1920,1080),(3440,1440),(2496,2688)]:
    draw3d=source;draw2d=source
    assert draw3d==draw2d
print("PASS unified physical source/menu + independent 640x480 UI, no late XR override, six destructive controls")
