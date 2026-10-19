#!/usr/bin/env python3
"""Contract for Virtual Desktop 2D source isolation from OpenXR eye allocation.

Tests are intentionally static and numeric; passing is not HMD validation.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
settings = (ROOT / "src/vr/settings.cpp").read_text(encoding="utf-8")
config = (ROOT / "src/hooks_misc.cpp").read_text(encoding="utf-8")
ex = (ROOT / "src/vr/d3d9/ex_device_upgrade.cpp").read_text(encoding="utf-8")

assert 'VRDesktopSourceCoordinates{ "VR", "DesktopSourceCoordinates", true,' in settings
assert 'Settings::VRDesktopSourceCoordinates.needs_restart();' in settings
assert 'extern Setting<bool> VRDesktopSourceCoordinates;' in config
assert 'extern Setting<bool> VRDesktopSourceCoordinates;' in ex

def verify_cfg(s):
    begin = s.index("void ApplyVrEyeResolutionAfterConfig(")
    end = s.index("class CommandLineArguments", begin)
    owner = s[begin:end]
    required = (
        "if (commandLineResolution)", "if (Settings::VRDesktopSourceCoordinates)",
        "GetSystemMetrics(SM_CXSCREEN)", "GetSystemMetrics(SM_CYSCREEN)",
        "desktopW >= 640 && desktopH >= 480",
        "static_cast<std::int64_t>(desktopW) * desktopH <= 16777216LL",
        "Game::screen_resolution->x = desktopW;",
        "Game::screen_resolution->y = desktopH;",
        'if (manualRequested)',
        'if (!Settings::VRAutoRenderResolution || !Settings::VRPreferD3D9Ex)'
    )
    for marker in required:
        assert marker in owner, marker
    idx = [owner.index(x) for x in (
        "if (commandLineResolution)",
        "if (Settings::VRDesktopSourceCoordinates)",
        "Game::screen_resolution->x = desktopW;",
        "return;",
        "if (manualRequested)",
        "if (!Settings::VRAutoRenderResolution || !Settings::VRPreferD3D9Ex)"
    )]
    # There is also an early return in the explicit resolution guard. Scope
    # the desktop lock's own return to the desktop branch.
    assert idx[0] < idx[1] < idx[2] < idx[4] < idx[5]
    desktop = owner.split("if (Settings::VRDesktopSourceCoordinates)",1)[1].split(
        "if (manualRequested)",1)[0]
    assert desktop.count("return;") == 2
    assert desktop.index("Game::screen_resolution->x = desktopW;") < desktop.index("return;")
    return True

def verify_ex(s):
    begin = s.index("OutRunVR::EyeExtent::Size ReadyXrEyeSizeAtCreateDevice(")
    end = s.index("Direct3DCreate9Fn OriginalDirect3DCreate9", begin)
    owner = s[begin:end]
    assert "Settings::VRDesktopSourceCoordinates ||" in owner
    assert owner.index("Settings::VRDesktopSourceCoordinates ||") < owner.index(
        "Settings::VRAutoRenderResolution")
    return True

verify_cfg(config)
verify_ex(ex)
for old, bad in (
    ("if (Settings::VRDesktopSourceCoordinates)", "if (false)"),
    ("Game::screen_resolution->x = desktopW;", "Game::screen_resolution->x = manualW;"),
    ("Game::screen_resolution->y = desktopH;", "Game::screen_resolution->y = manualH;"),
):
    try:
        verify_cfg(config.replace(old,bad,1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("desktop source contract escaped mutation: " + old)
try:
    verify_ex(ex.replace("Settings::VRDesktopSourceCoordinates ||", "false ||",1))
except (AssertionError, ValueError):
    pass
else:
    raise AssertionError("XR overwrite admission escaped negative mutation")

def select_source(desktop, config_ini, eye_extent, auto, manual, desktop_lock):
    w,h=desktop
    if desktop_lock and w>=640 and h>=480 and w*h<=16777216:
        return desktop
    if manual and min(manual)>=480: return manual
    return eye_extent if auto else config_ini

for desktop in [(1920,1080),(3440,1440),(2560,1600),(3840,2160)]:
    for configured in [(640,480),(1920,1080),(3440,1440)]:
        for auto in (False,True):
            assert select_source(desktop,configured,(2496,2688),auto,
                                 (3000,2400),True)==desktop
assert select_source((3440,1440),(640,480),(2496,2688),True,None,False)==(2496,2688)
print("PASS stable VD desktop 2D/source extent with XR eye allocation isolation, explicit opt-out, 4 destructive controls")
