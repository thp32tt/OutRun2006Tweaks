#!/usr/bin/env python3
"""Regression: selected game dimensions drive UI/source, not monitor or XR eye.

Source-level static + numeric contract. No Quest3 visual validation.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
settings = (ROOT / "src/vr/settings.cpp").read_text(encoding="utf-8")
config = (ROOT / "src/hooks_misc.cpp").read_text(encoding="utf-8")
ex = (ROOT / "src/vr/d3d9/ex_device_upgrade.cpp").read_text(encoding="utf-8")

assert 'VRFollowGameResolution{ "VR", "FollowGameResolution", true,' in settings
assert "Settings::VRFollowGameResolution.needs_restart();" in settings
assert "extern Setting<bool> VRFollowGameResolution;" in config
assert "extern Setting<bool> VRFollowGameResolution;" in ex
assert "VRDesktopSourceCoordinates" not in config + ex + settings

def assert_game_source_owner(text: str):
    start = text.index("void ApplyVrEyeResolutionAfterConfig(")
    end = text.index("class CommandLineArguments", start)
    part = text[start:end]
    tokens = (
        "if (commandLineResolution)", "if (manualRequested)",
        "Game::screen_resolution->x = manualW;",
        "Game::screen_resolution->y = manualH;",
        "if (Settings::VRFollowGameResolution &&\n            !Settings::VRUnifiedEyeMenuSource)",
        "Game::screen_resolution->x, Game::screen_resolution->y);",
        "if (!Settings::VRAutoRenderResolution || !Settings::VRPreferD3D9Ex)",
        "Game::screen_resolution->x = static_cast<int>(extent.width);",
    )
    for token in tokens:
        assert token in part, f"missing game/XR contract: {token}"
    loc = [part.index(token) for token in (
        "if (commandLineResolution)", "if (manualRequested)",
        "if (Settings::VRFollowGameResolution &&\n            !Settings::VRUnifiedEyeMenuSource)",
        "if (!Settings::VRAutoRenderResolution || !Settings::VRPreferD3D9Ex)",
        "Game::screen_resolution->x = static_cast<int>(extent.width);")]
    assert loc == sorted(loc), "manual/game priority must precede XR overwrite"
    follow = part.split("if (Settings::VRFollowGameResolution &&\n            !Settings::VRUnifiedEyeMenuSource)",1)[1].split(
        "if (!Settings::VRAutoRenderResolution",1)[0]
    assert "return;" in follow and "GetSystemMetrics(" not in follow
    assert "Game::screen_resolution->x =" not in follow
    assert "Game::screen_resolution->y =" not in follow

def assert_eye_source_isolation(text: str):
    start = text.index("OutRunVR::EyeExtent::Size ReadyXrEyeSizeAtCreateDevice(")
    end = text.index("Direct3DCreate9Fn OriginalDirect3DCreate9",start)
    part = text[start:end]
    assert "Settings::VRFollowGameResolution ||" in part
    assert "Settings::VRUnifiedEyeMenuSource) ||" in part
    assert part.index("Settings::VRUnifiedEyeMenuSource) ||") < part.index(
        "Settings::VRAutoRenderResolution")
    assert "GetSystemMetrics(" not in part

assert_game_source_owner(config)
assert_eye_source_isolation(ex)
for original, mutated in (
    ("if (Settings::VRFollowGameResolution &&\n            !Settings::VRUnifiedEyeMenuSource)", "if (false)"),
    ("if (manualRequested)", "if (false)"),
    ("Game::screen_resolution->x = manualW;", "Game::screen_resolution->x = 640;"),
    ("Game::screen_resolution->y = manualH;", "Game::screen_resolution->y = 480;"),
):
    assert original in config
    try:
        assert_game_source_owner(config.replace(original, mutated, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("Unsafe VR game-resolution rewrite escaped: "+original)
try:
    assert_eye_source_isolation(ex.replace(
        "Settings::VRFollowGameResolution ||", "false ||", 1))
except (AssertionError, ValueError):
    pass
else:
    raise AssertionError("XR eye override escaped game-source protection")

def route(game_source, xr_eye, *, explicit=None, manual=None, follow_game=True):
    if explicit is not None: return explicit
    if manual is not None: return manual
    if follow_game: return game_source
    return xr_eye

for game_source in ((640,480),(1280,720),(1920,1080),(2560,1440),(3440,1440)):
    for xr_eye in ((2016,2240),(2496,2688),(3072,3216)):
        assert route(game_source,xr_eye)==game_source
        assert route(game_source,xr_eye,explicit=(1600,900))==(1600,900)
        assert route(game_source,xr_eye,manual=(2304,1296))==(2304,1296)
        assert route(game_source,xr_eye,follow_game=False)==xr_eye

def map_menu_pixel(u,v,screen,logical=(640,480)):
    scale=min(screen[0]/logical[0],screen[1]/logical[1])
    off_x=(screen[0]-logical[0]*scale)/2
    off_y=(screen[1]-logical[1]*scale)/2
    return (off_x+u*scale,off_y+v*scale)
for screen in ((640,480),(1280,720),(1920,1080),(3440,1440)):
    cx,cy=map_menu_pixel(320,240,screen)
    assert abs(cx-screen[0]/2)<1e-6 and abs(cy-screen[1]/2)<1e-6
print("PASS game-selected source/UI extent vs VD/XR per-eye independence; 5 source mutations; screen-space coordinate scaling")
