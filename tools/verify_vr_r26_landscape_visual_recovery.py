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
assert 'exactCurrentChainOwner' in ui
assert 'FirstVerifiedAppendedNode(\n                        root, before[prio], tailAfter' in ui
assert 'VR RIVAL QUEUE PUBLICATION:' in ui
assert 'policy=EXACT_CURRENT_CHAIN' in ui
assert 'R30IsUnownedGoalFinalGraphPrimitiveUP' not in r30
assert 'VR GOAL FINAL GRAPH: FVF144 DPUP -> finite SCREEN_HUD stereo' not in r30
assert 'ResultProgressFullParentCallA = 0x98924' in ui
assert 'ResultProgressFullParentCallB = 0x992AC' in ui
assert 'ResultProgressFullParentTarget = 0x979E0' in ui
assert 'nullptr, &rootsBefore, entrySerial, true);' in ui
assert ui.count('if (self && self == submission.sprite)') >= 2
# Quest E deliberately restores both original 570008 children.
assert 'VR LENS 570008 ORIGINAL BOTH DRAWN:' in gfx
assert 'LensOuter570008Ordinal' in gfx
assert 'if (Settings::VREnabled && objectId == 0x570008' in gfx
assert 'ProducerToken::None);' in gfx
assert 'VR R69 FLARE FUSION:' in r30
print('PASS R26 XR/UI + AA2 + rival/+TIME/GOAL/lens exact-owner recovery source contract; HMD UNTESTED')

# Compile-shape guards for the XR/UI split source owner.
assert 'Hookclass CommandLineArguments' not in misc
assert 'OriginalDirect3DCreate9 = nullptr;        Direct3DCreate9Fn' not in ex
assert misc.count('class CommandLineArguments : public Hook') == 1
assert ex.count('Direct3DCreate9Fn OriginalDirect3DCreate9 = nullptr;') == 1

assert 'Game::screen_resolution->x, Game::screen_resolution->y);\n    }\n}\n\nclass CommandLineArguments : public Hook' in misc

# Reviewed visual fixes merged from Quest logs + DX9Ex automation reviews.
ui=(R/'src/hooks_uiscaling.cpp').read_text()
r30=(R/'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
gfx=(R/'src/hooks_graphics.cpp').read_text()
# AUTO 01473: foreign shared-vtable Flush/End cannot consume the tracked ledger.
assert 'if (self && self == submission.sprite)\n            HudBatch.completeNativeFlush' in ui
assert 'if (self && self == submission.sprite)\n            HudBatch.completeNativeEnd' in ui
# AUTO 01493/01476: no broad unowned GOAL/FVF144 promotion.
assert 'R30IsUnownedGoalFinalGraphPrimitiveUP' not in r30
assert 'VR GOAL FINAL GRAPH: FVF144 DPUP' not in r30
# Exact full-result parent remains the only bounded current-root result exception.
assert 'ProducerToken::ResultProgress,\n                nullptr, &rootsBefore, entrySerial, true' in ui
# AUTO 01504: +TIME itself must NOT use current-root rebuild ownership.
stage_leave=ui[ui.index('static void StageExtensionLeave'):ui.index('// The original GOAL animations')]
assert 'StageExtensionEntrySerial,\n                true' not in stage_leave
assert 'StageExtensionEntrySerial);' in stage_leave
# Quest E restores both original 570008 draw submissions; C993 retains
# the independent head-corrected centre-eye matrix.
assert 'VR LENS 570008 ORIGINAL BOTH DRAWN:' in gfx
assert 'if (ordinal == 2)' not in gfx
assert 'identityEye = IdentityMatrix()' in r30
assert 'mode=CENTRE_EYE_MONO_WORLD_LOCK' in r30
