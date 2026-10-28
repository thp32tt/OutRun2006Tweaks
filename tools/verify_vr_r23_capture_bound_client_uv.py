#!/usr/bin/env python3
"""R23 desktop pixels and game-client UV must share one capture generation."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'vrhost/src/main.cpp').read_text(encoding='utf-8')
R23=(ROOT/'vrhost/src/main_r23.cpp').read_text(encoding='utf-8')
WF=(ROOT/'.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')

for token in (
 'UvRect capturedGameUv_{};',
 'RECT capturedGameClient_{};',
 'bool capturedGameUvValid_ = false;',
 'std::uint64_t capturedGameOutputGeneration_ = 0;',
 'bool GetCapturedGameUv(',
 'capturedGameOutputGeneration_ != captureOutputGeneration_',
 'UvRect stereoSourceGameUv_{};',
 'bool stereoSourceGameUvValid_ = false;',
 'bool GetStereoSourceGameUv(',
 'stereoSourceGameOutputGeneration_ != captureOutputGeneration_',
):
    assert token in MAIN, token

bind=MAIN[MAIN.index('bool BindCaptureOutput(bool initial)'):MAIN.index('bool RecreateDuplication(', MAIN.index('bool BindCaptureOutput(bool initial)'))]
assert bind.index('capturedGameUvValid_ = false;') < bind.index('ReleaseCom(duplication_);')
assert bind.index('stereoSourceGameUvValid_ = false;') < bind.index('ReleaseCom(duplication_);')

ensure=MAIN[MAIN.index('bool EnsureSource('):MAIN.index('bool GetGameClientOutputRect(', MAIN.index('bool EnsureSource('))]
assert ensure.index('capturedGameUvValid_ = false;') < ensure.index('ReleaseCom(source_);')

commit=MAIN[MAIN.index('bool CommitStereoSource()'):MAIN.index('bool HasStereoSource()', MAIN.index('bool CommitStereoSource()'))]
for token in (
 '!capturedGameUvValid_',
 'capturedGameOutputGeneration_ != captureOutputGeneration_',
 'context_->CopyResource(stereoSource_, source_);',
 'stereoSourceGameUv_ = capturedGameUv_;',
 'stereoSourceGameClient_ = capturedGameClient_;',
 'stereoSourceGameOutputGeneration_ =',
 'capturedGameOutputGeneration_;',
 'stereoSourceGameUvValid_ = true;',
):
    assert token in commit, token
assert commit.index('CopyResource(stereoSource_, source_)') < commit.index('stereoSourceGameUvValid_ = true;')

projection=MAIN[MAIN.index('bool RenderProjection('):MAIN.index('bool RenderMenuPlaneTo(', MAIN.index('bool RenderProjection('))]
assert 'GetStereoSourceGameUv(whole, true)' in projection
assert 'c.GetGameUv(whole, true)' not in projection

capture=R23[R23.index('CaptureStatus R23Capture('):R23.index('CaptureStatus R23RefreshTheaterFallbackCapture(', R23.index('CaptureStatus R23Capture('))]
pointer=capture.index('CanSkipUnchangedPointerFrame(')
receipt=capture.index('UvRect acquiredGameUv{};')
copy=capture.index('CopyResource(c.source_, texture);')
release=capture.index('c.duplication_->ReleaseFrame();', copy)
publish=capture.index('c.capturedGameUvValid_ = acquiredGameUvValid;', release)
assert pointer < receipt < copy < release < publish
assert 'c.GetGameUv(\n            acquiredGameUv, false, &acquiredGameClient,' in capture
assert 'status.fullGameClientVisible =\n                c.capturedGameClientFullyVisible_;' in capture

r23proj=R23[R23.index('bool R23RenderProjection('):R23.index('bool R23RenderWorldLockedMenuProjection(', R23.index('bool R23RenderProjection('))]
assert 'GetStereoSourceGameUv(whole, true)' in r23proj
assert 'c.GetGameUv(whole)' not in r23proj
menu=R23[R23.index('bool R23RenderWorldLockedMenuProjection('):R23.index('bool R23RenderTheater(', R23.index('bool R23RenderWorldLockedMenuProjection('))]
assert 'GetCapturedGameUv(' in menu
assert 'c.GetGameUv(' not in menu
theater=R23[R23.index('bool R23RenderTheater('):R23.index('void R23CopyMatchedViews(', R23.index('bool R23RenderTheater('))]
assert 'GetCapturedGameUv(' in theater
assert 'c.GetGameUv(' not in theater

assert WF.count('tools/verify_vr_r23_capture_bound_client_uv.py') == 2

# Negative controls: either live-geometry reuse or pre-Release receipt publish must fail.
bad_menu=menu.replace('GetCapturedGameUv(', 'GetGameUv(', 1)
assert bad_menu != menu and 'c.GetGameUv(' in bad_menu
bad_order=capture.replace('c.capturedGameUvValid_ = acquiredGameUvValid;', '/* receipt omitted */', 1)
assert bad_order != capture and 'c.capturedGameUvValid_ = acquiredGameUvValid;' not in bad_order
print('PASS R23 source/stereo pixels carry capture-bound client UV receipt across pointer-only/timeout reuse; HMD UNTESTED')
