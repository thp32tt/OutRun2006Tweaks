#!/usr/bin/env python3
"""Destructive source regression for 00731 full-resolution same-Present fence readiness."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
HDR = (ROOT / "src/vr/d3d11/native_game_frame_publication.hpp").read_text()
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(source: str, header: str) -> bool:
    a = source.find("void before_game_present(")
    b = source.find("void before_game_reset()", a)
    if a < 0 or b <= a:
        return False
    section = source[a:b]
    queue = section.find("ctx->End(next.fence.Get());")
    flush = section.find("ctx->Flush();", queue)
    first = section.find("HRESULT ready = ctx->GetData(", flush)
    retry = section.find("GameNativeFramePublication::retry_same_present_fence(", first)
    upload = section.find("game->UpdateSurface(", retry)
    return all((
        0 <= queue < flush < first < retry < upload,
        "if (fullMode && fullQueued && ready == S_FALSE)" in section[first:retry],
        "QueryPerformanceCounter(&started)" in section[first:retry],
        "QueryPerformanceCounter(&now)" in section[retry:upload],
        "ready = ctx->GetData(oldest.fence.Get()" in section[retry:upload],
        "D3D11_ASYNC_GETDATA_DONOTFLUSH" in section[retry:upload],
        "if (ready == S_OK &&" in section[retry:upload],
        "oldest.provenance.may_present(s.presents, fullMode)" in section[retry:upload],
        "if (complete && outputWritable &&" in section[upload:],
        "s.sourceGameDevice == presentDevice && !fullMode" in section[upload:],
        "extraPolls < kMaxSamePresentExtraPolls" in header,
        "elapsedTicks < frequencyTicks / kSamePresentBudgetDivisor" in header,
        "fullMode && queuedNow &&" in header,
    ))

assert integrated(SRC, HDR), "native queued game output must poll same-Present fence with D3D9 fallback"
for old, new in (
    ("if (fullMode && fullQueued && ready == S_FALSE)", "if (fullMode && ready == S_FALSE)"),
    ("QueryPerformanceCounter(&now)", "/* removed deadline */ false"),
    ("ready = ctx->GetData(oldest.fence.Get()", "ready = S_OK; /* fake fence */ (oldest.fence.Get()"),
    ("oldest.provenance.may_present(s.presents, fullMode)", "oldest.provenance.may_overlay(s.presents)"),
):
    mutant = SRC.replace(old, new, 1)
    assert mutant != SRC and not integrated(mutant, HDR), old
for old, new in (
    ("fullMode && queuedNow &&", "fullMode || queuedNow ||"),
    ("extraPolls < kMaxSamePresentExtraPolls", "true"),
    ("elapsedTicks < frequencyTicks / kSamePresentBudgetDivisor", "true"),
):
    mutant = HDR.replace(old, new, 1)
    assert mutant != HDR and not integrated(SRC, mutant), old
assert "python tools/test_dx11_same_present_fence_00731.py" in WF
assert "tools/dx11_same_present_fence_probe_00731.cpp" in WF
print("00731 bounded full-native GPU readiness / same-Present D3D9 fallback PASS")
