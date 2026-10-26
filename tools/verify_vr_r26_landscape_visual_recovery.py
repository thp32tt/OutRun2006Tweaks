#!/usr/bin/env python3
from pathlib import Path
R=Path(__file__).resolve().parents[1]
settings=(R/'src/vr/settings.cpp').read_text()
ex=(R/'src/vr/d3d9/ex_device_upgrade.cpp').read_text()
ini=(R/'OutRun2006Tweaks.ini').read_text()
misc=(R/'src/hooks_misc.cpp').read_text()
run=(R/'tools/Run-DX9ExFocusTest.ps1').read_text()
ui=(R/'src/hooks_uiscaling.cpp').read_text()
r30=(R/'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
gfx=(R/'src/hooks_graphics.cpp').read_text()
assert 'VRAntiAliasing{ "VR", "AntiAliasing", 2,' in settings
assert 'VRAutoRenderResolution{ "VR", "AutoRenderResolution", true,' in settings
assert 'VRFollowGameResolution{ "VR", "FollowGameResolution", false,' in settings
assert 'VRUnifiedEyeMenuSource{ "VR", "UnifiedEyeMenuSource", false,' in settings
for x in ('AntiAliasing = 2','AutoRenderResolution = true',
          'FollowGameResolution = false','UnifiedEyeMenuSource = false',
          'Hud1080pReference = true','HudScale = 0.55','MenuScale = 1.00'):
    assert x in ini, x
assert 'physical D3D9Ex target will use live OpenXR eye extent at CreateDevice' in misc
assert 'Game::screen_resolution->x = static_cast<int>(xrSize.width)' not in ex
assert 'Game::screen_resolution->y = static_cast<int>(xrSize.height)' not in ex
assert 'physical D3D9Ex target=' in ex
for x in ("'-AutoRenderResolution=true'","'-FollowGameResolution=false'",
          "'-UnifiedEyeMenuSource=false'","'-AntiAliasing=2'",
          "'-Hud1080pReference=true'","'-HudScale=0.55'",
          "'-MenuScale=1.00'","'-CullingUnionMarginDegrees=8.0'"):
    assert x in run, x
assert 'VRHud1080pReference' in ui
assert 'spacing = 80.0f * Game::screen_scale->x;' in ui
assert '? 80.0f' in ui
assert 'exactRivalRootRebuild' in ui
assert 'FirstVerifiedAppendedNode(\n                        root, before[prio], tailAfter' in ui
assert 'VR RIVAL QUEUE PUBLICATION:' in ui
assert 'policy=EXACT_CURRENT_CHAIN' in ui
assert 'R30IsUnownedGoalFinalGraphPrimitiveUP' in r30
assert 'fvf != 0x00000144u' in r30
assert 'src != D3DBLEND_SRCALPHA' in r30
assert 'dst != D3DBLEND_INVSRCALPHA' in r30
assert 'VR GOAL FINAL GRAPH: FVF144 DPUP -> finite SCREEN_HUD stereo' in r30
assert 'ordinal <= 2' in gfx
assert 'VR LENS 570008 CHILD HIDDEN:' in gfx
print('PASS R26 XR-render/UI-split + F11/HUD/rival/GOAL/lens recovery source contract; HMD UNTESTED')

# Compile-shape guards for the XR/UI split source owner.
assert 'Hookclass CommandLineArguments' not in misc
assert 'OriginalDirect3DCreate9 = nullptr;        Direct3DCreate9Fn' not in ex
assert misc.count('class CommandLineArguments : public Hook') == 1
assert ex.count('Direct3DCreate9Fn OriginalDirect3DCreate9 = nullptr;') == 1

assert 'Game::screen_resolution->x, Game::screen_resolution->y);\n    }\n}\n\nclass CommandLineArguments : public Hook' in misc
