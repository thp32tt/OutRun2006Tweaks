#!/usr/bin/env python3
"""DX9Ex ESC/pause vertical FOV owner: source integration and negative mutation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
helper = (ROOT / "src/vr/d3d9/pause_menu_eye_affine.hpp").read_text(encoding="utf-8")
tests = (ROOT / "vrhost/tests/pause_menu_eye_affine_smoke.cpp").read_text(encoding="utf-8")

def check(s: str, h: str) -> None:
    assert '#include "pause_menu_eye_affine.hpp"' in s
    assert 'ExternalOverlaySemanticDepth == 0' in s
    assert 'GameState::STATE_SMPAUSEMENU' in s
    assert 'R30IsPauseMenuExactArrow()' in s
    assert s.count('R30PauseMenuVerticalAffine(') == 4
    for required in (
        'hudScaleY * pauseVertical.scale[eye] * ndcY',
        'eyeScaleY[0] * src[1] + eyeBiasY[0]',
        'eyeScaleY[1] * src[1] + eyeBiasY[1]',
        'clipCorrection._22 =',
        'hudScaleY * pauseVertical.scale[eye];',
        'clipCorrection._42 = pauseVertical.offset[eye] -',
        'leftDst[1] = transformedLeftY;',
        'rightDst[1] = transformedRightY;',
    ):
        assert required in s, required
    assert 'const float o = -sum[eye] / span[eye];' in h
    assert 'span[eye] <= 0.05f || span[eye] > 10.0f' in h
    assert 'return {};' in h
    assert 'failOne.valid' in tests and 'extreme.valid' in tests

check(source, helper)
for mutant in (
    source.replace('hudScaleY * pauseVertical.scale[eye] * ndcY',
                   'hudScaleY * ndcY', 1),
    source.replace('rightDst[1] = transformedRightY;',
                   'rightDst[1] = transformedLeftY;', 1),
    source.replace('clipCorrection._42 = pauseVertical.offset[eye] -',
                   'clipCorrection._42 =', 1),
    source.replace('ExternalOverlaySemanticDepth == 0',
                   'ExternalOverlaySemanticDepth != 0', 1),
):
    try:
        check(mutant, helper)
    except AssertionError:
        continue
    raise AssertionError("unsafe ESC mutation escaped verification")
print("DX9Ex ESC vertical affine source/mutation PASS")
