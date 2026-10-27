#!/usr/bin/env python3
from pathlib import Path
R=Path(__file__).resolve().parents[1]
ui=(R/'src/hooks_uiscaling.cpp').read_text()
sem=(R/'src/vr/game/render_semantics.hpp').read_text()
tail=(R/'src/vr/game/sprite_queue_tail_proof.hpp').read_text()
r30=(R/'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
ini=(R/'OutRun2006Tweaks.ini').read_text()
run=(R/'tools/Run-FocusOfficialTest.ps1').read_text()
settings=(R/'src/vr/settings.cpp').read_text()
a=ui.index('static int __cdecl RivalMarker_sprani(')
b=ui.index('// 2026-10-11 Quest3',a)
rv=ui[a:b]
assert rv.index('Game::sprani_play_ae_auth_alpha') < rv.index('const auto projectedAnchor = RivalMarkerProjectedInfo')
assert 'RivalMarkerProjectedInfo = {};' in rv
assert 'ScopedExactProducerSemantic' not in rv
assert 'FlushD3DXBeforeDirectGoalSource' not in rv
assert 'FlushD3DXAtDirectGoalSourceExit' not in rv
assert 'rootsBefore[prio] = root;' in rv and '&rootsBefore, entrySerial' in rv
assert 'VR RIVAL KNOWN-GOOD ORDER RESTORED:' in rv
assert 'FirstVerifiedNewRootAppendedChain' in tail
assert 'RivalNewRootRegression' in tail
assert 'rivalCreatedFreshRoot' in ui
assert '(*sourceRoots)[prio] == nullptr' in ui and 'before[prio] == nullptr' in ui
assert 'VR RIVAL FRESH ROOT RECOVERED:' in ui
assert 'ProjectedMarkerProbeStage::NativeSprite' in ui
assert 'VR RIVAL NATIVE QUEUE CONSUMER:' in ui
assert 'RivalDx11NativeRoute = false' in ini
assert "'-RivalDx11NativeRoute=false'" in run
assert 'VRRivalDx11NativeRoute{ "VR", "RivalDx11NativeRoute", false,' in settings
# Keep rival on historical identity-eye/IPD math. Rank-only experiments must
# remain guarded by exactOrdinalEyeCant, not RivalMarkerSprani token.
assert 'const bool exactOrdinalRank = marker->exactOrdinalEyeCant' in r30
assert 'ProducerToken::RivalMarkerSprani' not in r30[r30.index('bool R57BuildProjectedMarkerDelta('):r30.index('float R30HudAspectCompensation')]
print('PASS rival known-good native-first + null-root queue recovery + unchanged rival eye math; HMD UNTESTED')
