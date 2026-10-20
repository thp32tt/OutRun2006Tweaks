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
assert 'R30IsExactResultHudDraw()' in pose, 'R26 must scope eye cant to the exact result batch'
assert 'BuildStageEyePoses(' in pose, 'R26 drops the OpenXR eye orientations'
assert 'state.stereo.eyeOrientation' in pose
assert 'resultEyeOrientation[eye] : identityOrientation' in pose, 'unrelated HUD must retain its existing math'
assert 'if (!exactResult && CurrentVertexShaderIdentity.load(' in fixed, 'a stale cache must not veto an exact shaderless result'
assert 'device->GetVertexShader(&shader)' in fixed and 'shader->Release()' in fixed
assert 'fvf != 0x00000142u' in fixed, 'do not widen the live physical draw format'
assert 'VR R26 RESULT_HUD_EYES:' in fixed, 'record actual eye attempts and restoration'
assert 'return exactResult && !restored && SUCCEEDED(hr) ? E_FAIL : hr;' in fixed, 'do not report successful projection restoration after failure'
print('R26 result HUD pose/physical draw contract PASS')
