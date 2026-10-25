#!/usr/bin/env python3
from pathlib import Path
R=Path(__file__).resolve().parents[1]
settings=(R/'src/vr/settings.cpp').read_text()
ini=(R/'OutRun2006Tweaks.ini').read_text()
misc=(R/'src/hooks_misc.cpp').read_text()
run=(R/'tools/Run-DX9ExFocusTest.ps1').read_text()
ui=(R/'src/hooks_uiscaling.cpp').read_text()
r30=(R/'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
gfx=(R/'src/hooks_graphics.cpp').read_text()
assert 'VRAntiAliasing{ "VR", "AntiAliasing", 0,' in settings
assert 'VRAutoRenderResolution{ "VR", "AutoRenderResolution", false,' in settings
assert 'VRFollowGameResolution{ "VR", "FollowGameResolution", true,' in settings
assert 'VRUnifiedEyeMenuSource{ "VR", "UnifiedEyeMenuSource", false,' in settings
for x in ('AntiAliasing = 0','AutoRenderResolution = false',
          'FollowGameResolution = true','UnifiedEyeMenuSource = false',
          'Hud1080pReference = true','HudScale = 0.55','MenuScale = 1.00'):
    assert x in ini, x
assert 'if (extent.width <= extent.height)' in misc
assert 'VR SOURCE SPLIT:' in misc
for x in ("'-AutoRenderResolution=false'","'-FollowGameResolution=true'",
          "'-UnifiedEyeMenuSource=false'","'-AntiAliasing=0'",
          "'-Hud1080pReference=true'","'-HudScale=0.55'",
          "'-MenuScale=1.00'","'-CullingUnionMarginDegrees=8.0'"):
    assert x in run, x
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
print('PASS R26 landscape/F11/HUD/rival/GOAL/lens recovery source contract; HMD UNTESTED')
