#!/usr/bin/env python3
"""Check the R26 +TIME/GOAL historical finite-HUD pose rollback.

Exact result ownership still controls provenance, batching and the stale-shader
cache exception. Placement itself must match the stable R26 finite HUD path:
HeadInverse once, head-relative eye translation, identity eye orientation.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / 'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
pose = src[src.index('bool R30ConfigureXyzrhwWorldEffect('):src.index('bool R30TransformXyzrhwVertices(')]
fixed = src[src.index('HRESULT R62TryFixedFunctionSpriteStereo('):src.index('HRESULT __stdcall DrawPrimitiveDestR30(')]
shader_hud = src[src.index('bool R30BuildScreenSpaceEyeConstants('):src.index('template <typename ActualDraw>\n        HRESULT R30TryScreenSpaceFovDraw(')]
xy_prepare = src[src.index('bool R30PrepareXyzrhwState('):src.index('bool R30XyzrhwHasProjectedDepthSignature(')]
assert 'BuildStageEyePoses(' not in pose, 'result HUD must not re-apply eye-local rotation'
assert 'resultEyeOrientation' not in pose and 'resultEyeOffset' not in pose
assert 'identityOrientation, relativeEye' in pose, 'fixed-function result HUD must use stable R26 eye transform'
assert 'BuildStageEyePoses(' not in shader_hud, 'shader result HUD must not re-apply eye-local rotation'
assert 'resultEyeOrientation' not in shader_hud and 'resultEyeOffset' not in shader_hud
assert 'identityOrientation, relativeEye, worldScale' in shader_hud, 'shader result HUD must use stable R26 eye transform'
assert 'const bool exactResult = R30IsExactResultHudDraw();' in xy_prepare, 'XYZRHW prepare must identify exact result before cached-VS gate'
assert 'if (!exactResult &&' in xy_prepare and 'device->GetVertexShader(&shader)' in xy_prepare, 'exact XYZRHW result must use live VS as authority'
assert 'if (!exactResult && CurrentVertexShaderIdentity.load(' in fixed, 'a stale cache must not veto an exact shaderless result'
assert 'device->GetVertexShader(&shader)' in fixed and 'shader->Release()' in fixed
assert 'fvf != 0x00000142u' in fixed, 'do not widen the live physical draw format'
assert 'VR R26 RESULT_HUD_EYES:' in fixed, 'record actual eye attempts and restoration'
assert 'return exactResult && !restored && SUCCEEDED(hr) ? E_FAIL : hr;' in fixed, 'do not report successful projection restoration after failure'

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