#!/usr/bin/env python3
from pathlib import Path
R=Path(__file__).resolve().parents[1]
ui=(R/'src/hooks_uiscaling.cpp').read_text()
sem=(R/'src/vr/game/render_semantics.hpp').read_text()
tail=(R/'src/vr/game/sprite_queue_tail_proof.hpp').read_text()
r30=(R/'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
r84=(R/'src/vr/d3d9/stereo_renderer_r30.cpp').read_text()
r33=(R/'src/vr/d3d9/stereo_renderer_r33.cpp').read_text()
ini=(R/'OutRun2006Tweaks.ini').read_text()
run=(R/'tools/Run-FocusOfficialTest.ps1').read_text()
profiles=(R/'tools/OutRunVR-TestProfiles.ps1').read_text()
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
# Native-projector A/B may keep stock BB6F0, but BB796 ownership is
# mandatory in both modes; otherwise all projected/fresh-root fixes are bypassed.
assert 'BB796 ownership is NOT optional' in ui
assert 'BB796 ownership remains active but exact-edge anchor provenance is not forced' in ui
assert 'if (!Settings::VRRivalDx11NativeRoute.get())\n            Memory::VP::InjectHook(\n                Module::exe_ptr(RivalMarker_SpraniCall)' not in ui
assert 'stockProjectorAB={} exactEdgeRequested={} BB796Ownership=ALWAYS' in settings
assert 'VR RIVAL BB796 OWNERSHIP: installed=1 exactEdgeRequested={} exactEdgeInstalled={} stockProjectorAB={}' in ui
assert 'rivalExactEdgeRequested && Calc3D2D_hk' in ui
assert 'reason=CALC3D2D_TRAMPOLINE_UNAVAILABLE' in ui
assert 'FirstVerifiedNewRootAppendedChain' in tail
assert 'RivalNewRootRegression' in tail
assert 'rivalCreatedFreshRoot' in ui
assert '(*sourceRoots)[prio] == nullptr' in ui and 'before[prio] == nullptr' in ui
assert 'VR RIVAL FRESH ROOT RECOVERED:' in ui
assert 'ProjectedMarkerProbeStage::NativeSprite' in ui
assert 'VR RIVAL NATIVE QUEUE CONSUMER:' in ui
assert 'RivalDx11NativeRoute = false' in ini
assert 'UIScalingMode = 1' in ini
assert "'-RivalDx11NativeRoute=false'" in run
assert "'-UIScalingMode=1'" in run
assert "'-RivalDx11NativeRoute=false'" in profiles
assert "'-UIScalingMode=1'" in profiles
assert 'VRRivalDx11NativeRoute{ "VR", "RivalDx11NativeRoute", false,' in settings
# Keep rival on historical identity-eye/IPD math. Rank-only experiments must
# remain guarded by exactOrdinalEyeCant, not RivalMarkerSprani token.
assert 'const bool exactOrdinalRank = marker->exactOrdinalEyeCant' in r30
assert 'ProducerToken::RivalMarkerSprani' not in r30[r30.index('bool R57BuildProjectedMarkerDelta('):r30.index('float R30HudAspectCompensation')]

# Known-good a22be86a always reached the live DPUP XYZRHW probe before R33
# shader dispatch. Keep the modern cache fast-path for unrelated draws, but
# exact rival ownership must reach authoritative live GetVertexShader/GetFVF.
dpup_a=r33.index('HRESULT __stdcall DrawPrimitiveUPDestR33(')
dpup_b=r33.index('HRESULT __stdcall DrawIndexedPrimitiveUPDestR33(',dpup_a)
dpup=r33[dpup_a:dpup_b]
plain_a=r33.index('HRESULT __stdcall DrawPrimitiveDestR33(')
plain_b=r33.index('HRESULT __stdcall DrawIndexedPrimitiveDestR33(',plain_a)
plain=r33[plain_a:plain_b]
for token in (
    'const bool exactProjectedRival =',
    'ProducerToken::RivalMarkerSprani',
    'CurrentProjectedMarker() != nullptr',
    '(exactProjectedRival ||',
    'R32ReviewTryXyzrhwPrimitiveUP(',
):
    assert token in dpup, token
assert 'const bool exactProjectedRival =' not in plain
assert r30.count('const bool exactProjectedRival =') >= 2
assert '!exactResult && !exactProjectedRival' in r30
assert 'R30XyzrhwPrepareRejectName' in r30
assert 'safeBase={}' in r30
assert 'R9_NOT_SEEDED' in r30
assert 'DEPTH_NOT_MIRRORABLE' in r30
assert 'ACTIVE_OCCLUSION_QUERY' in r30
assert 'LIVE_VS_BOUND' in r30 and 'FVF_NOT_XYZRHW' in r30
assert 'VR RIVAL R30 SHADER CACHE ZERO:' in r30
rank_phys=(R/'src/vr/game/rank_marker_physical_source.hpp').read_text()
assert 'ProducerToken::RivalMarkerSprani' in rank_phys
assert 'raw.queueNode == physical.queueNode' in rank_phys
assert 'raw.queueEpoch == physical.queueEpoch' in rank_phys
assert 'physical.drawSerial - raw.writtenDraw <= 12u' in rank_phys
assert 'VR RIVAL R33 RAW C64 FENCE:' in r33
assert 'GetLastGameWvpProjectedMarker' in r33
assert 'rawAnchorValid={}' in r33
assert 'rawAnchorMatch={}' in r33
assert 'VR RIVAL R33 OUTER GUARD:' in r33
assert 'STATEBLOCK_RECORDING' in r33
assert 'STEREO_NOT_WANTED' in r33
assert 'NOT_BACKBUFFER' in r33

# D3DX/FVF142 projected rival uses the same exact-source exception: cached
# shader shadow may not veto the route, but live VS and exact FVF 0x142 remain
# mandatory before any eye draw.
r62_a=r30.index('HRESULT R62TryFixedFunctionSpriteStereo(')
r62_b=r30.index('HRESULT R62TryFixedFunctionSpriteIndexed(',r62_a)
r62=r30[r62_a:r62_b]
for token in (
    'const bool exactProjectedRival =',
    'ProducerToken::RivalMarkerSprani',
    'sourceCommand.queued && sourceCommand.queueNode',
    '!exactResult && !exactProjectedRival',
    'device->GetVertexShader(&shader)',
    'fvf != 0x00000142u',
    'VR RIVAL R62 FIXEDFN PREPARE:',
    'const bool tracePhysicalEyes =',
    '(exactResult || exactProjectedRival)',
    'VR RIVAL R62 FIXEDFN EYE RECEIPT:',
):
    assert token in r62, token

# Do not restore the old per-Draw rival Flush. Modern D3DX may defer an exact
# vehicle marker command, so submit only while its current queue node/epoch/
# anchor are still authoritative at NEXT_NODE or QUEUE_END. Rank 1/2/3
# sprani and rank 4/5 clip digits intentionally share the exact rival boundary
# without weakening the rival proof.
for token in (
    'static bool FlushExactVehicleMarkerAtQueueBoundary(',
    'ProjectedVehicleMarkerOwner(',
    'ProducerToken::RivalMarkerSprani',
    'ProducerToken::RankMarkerSprani',
    'ProducerToken::RankMarkerClipSprite',
    'HudBatch.matchesGpuOwner(',
    'CurrentProjectedMarker()',
    'FlushExactVehicleMarkerAtQueueBoundary("NEXT_NODE")',
    'FlushExactVehicleMarkerAtQueueBoundary("QUEUE_END")',
    'VR VEHICLE MARKER D3DX QUEUE BOUNDARY FLUSH:',
):
    assert token in ui, token
assert 'VR RIVAL R84 RAW C64 PROOF:' in r84

print('PASS rival known-good BB796 ownership preserved + rank 1-5 share exact projected vehicle queue boundary + native-first/null-root/live DPUP/R62/R33 proofs retained; HMD UNTESTED')
