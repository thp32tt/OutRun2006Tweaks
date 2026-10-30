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
gfx=(r/"src/hooks_graphics.cpp").read_text()
assert "Game::screen_resolution->x = 1920;" in misc and "Game::screen_resolution->y = 1080;" in misc
assert "fixedLogicalVr ? 1920" in misc and "fixedLogicalVr ? 1080" in misc
assert misc.index("if (commandLineResolution)") < misc.index("VR R26 LOGICAL SOURCE LOCK:")
assert "ResolveStartupForLiveHost(" in ex and "ResolveGame(extent, capsSize)" in ex
assert "GetTickCount64() + 8000ULL" in ex and "Sleep(50);" in ex
assert "state == GameState::STATE_TIMEUP" in ui and "ResultPresentationState()" in ui
assert "ResultProgressAdmission.mayPublish(" in ui and "parentAdmission.mayPublish(" in ui
assert "RivalDx11NativeRoute = false" in ini and "'-RivalDx11NativeRoute=false'" in run
assert "MirrorPreserveAspect = true" in ini and "'-MirrorPreserveAspect=true'" in run
assert 'getboolean("VR","RivalDx11NativeRoute") is False' in flow
assert 'getboolean("VR","MirrorPreserveAspect") is True' in flow
assert "foreach ($mode in @(\'TEST\',\'DEBUG\'))" in flow
assert "mirror_backdrop_window" in gfx and "update_mirror_backdrop(" in gfx
print("Quest D log/source/packaging static PASS; HMD untested")
