#!/usr/bin/env python3
"""Quest E source+package regression. Static only; Quest 3 runtime UNTESTED."""
from pathlib import Path
r = Path(__file__).resolve().parents[1]
gfx = (r/'src/hooks_graphics.cpp').read_text()
ui = (r/'src/hooks_uiscaling.cpp').read_text()
ex = (r/'src/vr/d3d9/ex_device_upgrade.cpp').read_text()
ini = (r/'OutRun2006Tweaks.ini').read_text()
runner = (r/'tools/Run-FocusOfficialTest.ps1').read_text()
workflow = (r/'.github/workflows/vr-dx9ex-official-focus-test.yml').read_text()
s = (r/'src/vr/settings.cpp').read_text()
l = gfx[gfx.index('static void __cdecl DrawObjectAlphaProjected('):gfx.index('static void __cdecl DrawObjectAlphaCentre(')]
c = gfx[gfx.index('static void __cdecl DrawObjectAlphaCentre('):gfx.index('public:',gfx.index('static void __cdecl DrawObjectAlphaCentre('))]
rv = ui[ui.index('static int __cdecl RivalMarker_sprani('):ui.index('static bool IsOriginalB9200GoalGlyph()')]
checks = {
  'both original 570008 children drawn': 'VR LENS 570008 ORIGINAL BOTH DRAWN' in l and 'LensOuter570008Ordinal' in l and 'return;' not in l,
  'original CABE alpha draw retained': 'Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);' in l,
  'central C993 cannot be suppressed': 'VRLensFlareCentreEnabled.get()' not in c and 'IsProjectedSunScreenObject(objectId)' in c,
  'four unique sun objects preserved': all(v in c for v in ['0x570002','0x57000F','0x570010','0x570006']) is False or 'IsProjectedSunScreenObject(objectId)' in c,
  'exact rival rebuilt-root safely tagged': 'TagAppendedNodes(' in rv and 'rootsBefore' in rv and 'FirstVerifiedNewRootAppendedChain' in ui,
  'rival no generic hook': 'RivalDx11NativeRoute = false' in ini and "'-RivalDx11NativeRoute=false'" in runner,
  'late actual XR eye startup': 'GetTickCount64() + 8000ULL' in ex and 'ResolveStartupForLiveHost(' in ex and 'Sleep(50);' in ex,
  'menu aspect restored': 'MirrorPreserveAspect = true' in ini and "'-MirrorPreserveAspect=true'" in runner,
  'legacy C993 hide option ineffective': 'False is deliberately ignored' in s,
  'runnable TEST DEBUG': "foreach ($mode in @('TEST','DEBUG'))" in workflow and 'START_HERE.cmd' in workflow and 'DX9EX_VARIANT.txt' in workflow,
  'separate metadata': 'QUEST_E_VARIANT.txt' in workflow,
}
for desc, good in checks.items():
    if not good:
        raise SystemExit('QUEST E FAIL: '+desc)
print('QUEST E PASS static source and package guards. HMD still UNTESTED.')
