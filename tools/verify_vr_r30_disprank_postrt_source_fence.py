#!/usr/bin/env python3
"""DispRank FVF142 must retain exact source identity through RIGHT setup."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src/vr/d3d9/stereo_renderer_r30.cpp'
WORKFLOW = ROOT / '.github/workflows/vr-dx9ex-active.yml'

def body(source: str, signature: str) -> str:
    at = source.index(signature)
    start = source.index('{', at)
    depth = 0
    for pos in range(start, len(source)):
        if source[pos] == '{':
            depth += 1
        elif source[pos] == '}':
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise AssertionError('unclosed ' + signature)

def check(source: str) -> bool:
    try:
        fn = body(source, 'HRESULT R30ExecuteXyzrhwStereo(')
        before = fn.index('const auto fixedRankBefore = protectFixedFnRankHud')
        left = fn.index('const HRESULT leftHr = leftDraw();', before)
        first = fn.index('SameFixedFnRankHudAfterLeft(', left)
        rt = fn.index('R29OwnerCallOriginalSetRenderTarget(', first)
        viewport = fn.index('device->SetViewport(&state.viewport);', rt)
        second = fn.index('SameFixedFnRankHudAfterLeft(', viewport)
        right = fn.index('rightHr = rightDraw();', second)
        assert before < left < first < rt < viewport < second < right
        right_gate = fn[viewport:right]
        assert 'SUCCEEDED(rightHr) && protectFixedFnRankHud' in right_gate
        assert 'fixedRankBefore, captureFixedRankHud()' in right_gate
        assert 'StereoFailureRightStateFailed' in right_gate
        assert 'rightHr = E_FAIL;' in right_gate
        assert fn.count('SameFixedFnRankHudAfterLeft(') >= 2
        return True
    except (AssertionError, ValueError):
        return False

def main() -> None:
    source = SRC.read_text(encoding='utf-8')
    workflow = WORKFLOW.read_text(encoding='utf-8')
    assert workflow.count('tools/verify_vr_r30_disprank_postrt_source_fence.py') == 2
    assert check(source), 'DispRank post-RT/pre-RIGHT source fence missing'
    second = source.find('SameFixedFnRankHudAfterLeft(',
        source.find('SameFixedFnRankHudAfterLeft(') + 1)
    assert second >= 0
    close = source.find('                if (SUCCEEDED(rightHr))', second)
    assert close > second
    mutated = source[:source.rfind('                // DispRank\'s fixed-function FVF142 route', 0, second + 1)] + source[close:]
    assert mutated != source
    assert not check(mutated), 'removing post-RT rank fence escaped verifier'
    print('PASS R30 DispRank FVF142 source stamp survives LEFT and is revalidated after RIGHT RT/depth/viewport setup; HMD UNTESTED')

if __name__ == '__main__':
    main()
