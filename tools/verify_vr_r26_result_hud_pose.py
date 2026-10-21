#!/usr/bin/env python3
"""Check the R26 result-only eye-pose/physical shader transaction wiring.

Numerical eye-pose behavior is covered by stage_extension_eye_plane_smoke.
This contract prevents the compiled R26 owner silently retaining identity
eyes or rejecting shaderless D3DX from an unrelated cached shader identity.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / 'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
pose = src[src.index('bool R30ConfigureXyzrhwWorldEffect('):src.index('bool R30TransformXyzrhwVertices(')]
fixed = src[src.index('HRESULT R62TryFixedFunctionSpriteIndexed('):src.index('HRESULT __stdcall DrawPrimitiveDestR30(')]
shader_hud = src[src.index('bool R30BuildScreenSpaceEyeConstants('):src.index('template <typename ActualDraw>\n        HRESULT R30TryScreenSpaceFovDraw(')]
xy_prepare = src[src.index('bool R30PrepareXyzrhwState('):src.index('bool R30XyzrhwHasProjectedDepthSignature(')]
assert 'R30IsExactResultHudDraw()' in pose, 'R26 must scope eye cant to the exact result batch'
assert 'BuildStageEyePoses(' in pose, 'R26 drops the OpenXR eye orientations'
assert 'state.stereo.eyeOrientation' in pose
assert 'resultEyeOrientation[eye] : identityOrientation' in pose, 'unrelated HUD must retain its existing math'
assert 'const bool exactResult = R30IsExactResultHudDraw();' in shader_hud, 'shader HUD must scope eye cant to exact result ownership'
assert 'BuildStageEyePoses(' in shader_hud and 'stereo.eyeOrientation' in shader_hud, 'shader result HUD drops head-local eye rotation'
assert 'exactResult ? resultEyeOrientation[eye] : identityOrientation' in shader_hud, 'generic shader HUD must keep legacy identity-eye math'
assert 'const bool exactResult = R30IsExactResultHudDraw();' in xy_prepare, 'XYZRHW prepare must identify exact result before cached-VS gate'
assert 'if (!exactResult &&' in xy_prepare and 'device->GetVertexShader(&shader)' in xy_prepare, 'exact XYZRHW result must use live VS as authority'
assert 'if (!exactResult && CurrentVertexShaderIdentity.load(' in fixed, 'a stale cache must not veto an exact shaderless result'
assert 'device->GetVertexShader(&shader)' in fixed and 'shader->Release()' in fixed
assert 'fvf != 0x00000142u' in fixed, 'do not widen the live physical draw format'
assert 'VR R26 RESULT_HUD_EYES:' in fixed, 'record actual eye attempts and restoration'
assert 'return !restored && SUCCEEDED(hr) ? E_FAIL : hr;' in fixed, 'all R62 owners must report projection restoration failure'

# A non-exact R62 draw can also leave the game projection stale; reject the
# old exactResult-only condition (without changing R62 draw/restore ordering).
assert "return exactResult && !restored && SUCCEEDED(hr) ? E_FAIL : hr;" not in fixed, (
    "non-result rank/HUD R62 restores must not silently return S_OK")

# A cached-zero shader can be intentional R13 masking: observe it in a
# bounded opt-in probe, but never promote live device VS to original c64 proof.
shader_gate = shader_hud.split('if (screenKind == R30ScreenSpaceKind::PerspectiveHud ||', 1)[0]
assert 'CurrentVertexShaderIdentity.load(' in shader_gate, 'do not bypass original shader identity guard'
assert 'if (Settings::VRTelemetry && R30IsExactResultHudDraw())' in shader_gate, 'probe only source-proven exact result with telemetry on'
assert 'RESULT_HUD_SHADER_GATE: decision=FALLBACK_CACHE_ZERO' in shader_gate, 'diagnose zero-cache physical shader ambiguity'
assert 'poseSeq={} drawSerial={}' in shader_gate and 'TopLevelDrawSerial() + 1u' in shader_gate, 'correlate one exact GPU draw with a single pose and serial'
assert 'device->GetVertexShader(&liveVs)' in shader_gate and 'liveVs->Release()' in shader_gate, 'release any observed live shader'
assert '                return false;\n            }' in shader_gate, 'live shader diagnosis must not promote R26 source'
indexed_dispatch = src[src.index('HRESULT __stdcall DrawIndexedPrimitiveDestR30('):src.index('HRESULT __stdcall DrawPrimitiveUPDestR30(')]
assert 'stage=R62_ONLY finalRoute=UNDETERMINED api=DIP' in indexed_dispatch, 'R62 failed candidate is not terminal HUD rejection'

print('R26 result HUD pose/physical draw contract PASS')
