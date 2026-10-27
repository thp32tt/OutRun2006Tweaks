#!/usr/bin/env python3
"""Recovery theater crop must follow the exact copied capture, not an unrelated Frame.v2 snapshot."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT/'vrhost/src/main.cpp').read_text(encoding='utf-8')
R23 = (ROOT/'vrhost/src/main_r23.cpp').read_text(encoding='utf-8')
WF = (ROOT/'.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')

def check(main: str, r23: str) -> bool:
    try:
        for token in (
            'bool capturedLayoutKnown_ = false;',
            'bool capturedLayoutSbs_ = false;',
            'std::int64_t capturedLayoutPresentQpc_ = 0;',
            'std::uint64_t capturedLayoutOutputGeneration_ = 0;',
        ): assert token in main
        bind = main[main.index('bool BindCaptureOutput(bool initial)'):main.index('bool RecreateDuplication(bool initial)')]
        for token in ('capturedLayoutKnown_ = false;', 'capturedLayoutSbs_ = false;',
                      'capturedLayoutPresentQpc_ = 0;', 'capturedLayoutOutputGeneration_ = 0;'):
            assert token in bind
        copied = r23[r23.index('if (copied)'):r23.index('return status;', r23.index('if (copied)'))]
        assert 'c.capturedLayoutKnown_ = false;' in copied
        assert 'c.capturedLayoutOutputGeneration_ = 0;' in copied
        select = r23.index('R23SelectClassicFrameForCapture(')
        receipt = r23.index('compositor.capturedLayoutKnown_ = true;', select)
        assert receipt > select
        fallback = r23[r23.index('const bool receiptMatchesCapture'):r23.index('if (fallbackCapture.available &&\n                            R23RenderTheater', r23.index('const bool receiptMatchesCapture'))]
        for token in (
            'compositor.capturedLayoutKnown_',
            'compositor.capturedLayoutSbs_',
            'compositor.capturedLayoutPresentQpc_ ==',
            'fallbackCapture.lastPresentQpc',
            'compositor.capturedLayoutOutputGeneration_ ==',
            'compositor.captureOutputGeneration_',
            'fallbackCapture.fresh',
            'R23SelectClassicFrameForCapture(',
            'renderFrames, fallbackCapture, 0u,',
            'const bool fallbackSourceIsSbs =',
            'receiptMatchesCapture();',
        ): assert token in fallback, token
        assert 'before.state == OutRunVR::StereoSbsActive' not in fallback
        assert '(before.flags & OutRunVR::RenderFrameStereoComplete)' not in fallback
        return True
    except (AssertionError, ValueError):
        return False

assert WF.count('tools/verify_vr_recovery_theater_capture_layout_receipt.py') == 2
assert check(MAIN, R23)
mut = R23.replace('compositor.capturedLayoutPresentQpc_ ==\n                                    fallbackCapture.lastPresentQpc', 'true', 1)
assert mut != R23 and not check(MAIN, mut), 'QPC receipt mutation escaped'
mut = R23.replace('compositor.capturedLayoutOutputGeneration_ ==\n                                    compositor.captureOutputGeneration_', 'true', 1)
assert mut != R23 and not check(MAIN, mut), 'output generation mutation escaped'
print('PASS recovery theater SBS crop is capture-QPC/output-generation bound; HMD UNTESTED')
