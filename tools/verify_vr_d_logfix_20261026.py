#!/usr/bin/env python3
"""Quest 3 log-derived exact-source negative controls; HMD still UNTESTED."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
misc=(r/"src/hooks_misc.cpp").read_text()
ui=(r/"src/hooks_uiscaling.cpp").read_text()
ex=(r/"src/vr/d3d9/ex_device_upgrade.cpp").read_text()
ini=(r/"OutRun2006Tweaks.ini").read_text()
run=(r/"tools/Run-FocusOfficialTest.ps1").read_text()
flow=(r/".github/workflows/vr-dx9ex-official-focus-test.yml").read_text()
assert "Game::screen_resolution->x = 1920;" in misc and "Game::screen_resolution->y = 1080;" in misc
assert "fixedLogicalVr ? 1920" in misc and "fixedLogicalVr ? 1080" in misc
assert misc.index("if (commandLineResolution)") < misc.index("VR R26 LOGICAL SOURCE LOCK:")
assert "ResolveStartupForLiveHost(" in ex and "ResolveGame(extent, capsSize)" in ex
assert "GetTickCount64() + 8000ULL" in ex and "Sleep(50);" in ex
assert "state == GameState::STATE_TIMEUP" in ui and "ResultPresentationState()" in ui
assert "ResultProgressAdmission.mayPublish(" in ui and "parentAdmission.mayPublish(" in ui
assert "RivalDx11NativeRoute = false" in ini and "'-RivalDx11NativeRoute=false'" in run
# 2026-10-28 user request supersedes Quest D's narrower 2560x1440 PC mirror.
# Retain the historical source contract; in VR the mirror now fills 3440x1440.
assert "MirrorPreserveAspect = false" in ini and "'-MirrorPreserveAspect=false'" in run
assert 'getboolean("VR","RivalDx11NativeRoute") is False' in flow
assert 'getboolean("VR","MirrorPreserveAspect") is False' in flow
assert "foreach ($mode in @(\'TEST\',\'DEBUG\'))" in flow
print("Quest D log/source/packaging static PASS; HMD untested")
