#!/usr/bin/env python3
"""00745 actual full-frame D3D11 Map->D3D9 UpdateSurface failure isolation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
HDR = (ROOT / "src/vr/d3d11/native_game_frame_publication.hpp").read_text()
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(src, hdr):
    first = src.find("void before_game_present(")
    last = src.find("void before_game_reset(", first)
    if first < 0 or last < first: return False
    body = src[first:last]
    fence = body.find("if (ready == S_OK")
    mapping = body.find("ctx->Map(oldest.staging.Get()", fence)
    classify = body.find("GameNativeFramePublication::classify_map(", mapping)
    ready = body.find("if (mapResult == GameNativeReadbackMap::Ready)", classify)
    copy = body.find("game->UpdateSurface(", ready)
    failure = body.find("mapResult == GameNativeReadbackMap::Failed", copy)
    unmap = body.find("if (mapStatus == S_OK) ctx->Unmap(", failure)
    quarantine = body.find("oldest.quarantined = true;", unmap)
    end = body.find("} else if (GameNativeFramePublication::classify_fence(", quarantine)
    if not (0 <= fence < mapping < classify < ready < copy < failure < unmap < quarantine < end):
        return False
    return all((
        "mapStatus == S_OK" in body[unmap:quarantine],
        "oldest.busy = false;" not in body[failure:end],
        "status == stillDrawingStatus" in hdr,
        "status == 0 && hasPixels && valid_readback_pitch(width, rowPitch)" in hdr,
        "GameNativeReadbackMap::Failed" in hdr,
        "if (fullMode && fullQueued &&" in body[mapping:ready],
        "if (fullMode && fullQueued &&\n                        mapResult == GameNativeReadbackMap::Pending)" in body[mapping:ready],
        "GameNativeFramePublication::retry_same_present_map(" in body[mapping:ready],
        "QueryPerformanceCounter(&startedMap)" in body[mapping:ready],
        "QueryPerformanceCounter(&nowMap)" in body[mapping:ready],
        "mapStatus = ctx->Map(oldest.staging.Get()" in body[mapping:ready],
        "D3D11_MAP_FLAG_DO_NOT_WAIT" in body[mapping:ready],
        "mapResult != GameNativeReadbackMap::Pending) break;" in body[mapping:ready],
        "mapPending && queuedNow && fullMode &&" in hdr,
        "extraPolls < kMaxSamePresentMapExtraPolls" in hdr,
        "elapsedTicks < frequencyTicks / kSamePresentMapBudgetDivisor" in hdr,
    ))

assert integrated(SRC, HDR), "failed Map must not recycle staging or touch D3D9 upload"
for old, new in (
    ("if (mapResult == GameNativeReadbackMap::Ready)",
     "if (SUCCEEDED(mapStatus))"),
    ("oldest.quarantined = true;", "oldest.busy = false;"),
    ("mapResult == GameNativeReadbackMap::Failed", "mapStatus == S_OK"),
):
    mutant = SRC.replace(old, new, 1)
    assert mutant != SRC and not integrated(mutant, HDR), old
for old, new in (
    ("status == stillDrawingStatus", "status != stillDrawingStatus"),
    ("status == 0 && hasPixels && valid_readback_pitch(width, rowPitch)",
     "status >= 0 && hasPixels"),
):
    mutant = HDR.replace(old, new, 1)
    assert mutant != HDR and not integrated(SRC, mutant), old

# Destructive source/contract checks: never turn a pending Map into a
# blocking wait, reuse stale frames or remove the original D3D9 fallback.
for old, new in (
    ("mapStatus = ctx->Map(oldest.staging.Get()", "mapStatus = S_OK; /* forced */ (oldest.staging.Get()"),
    ("mapResult == GameNativeReadbackMap::Pending", "mapResult != GameNativeReadbackMap::Pending"),
    ("QueryPerformanceCounter(&nowMap)", "false /* no deadline */"),
):
    mutant = SRC.replace(old, new, 1)
    assert mutant != SRC and not integrated(mutant, HDR), old
for old, new in (
    ("mapPending && queuedNow && fullMode &&", "mapPending || queuedNow || fullMode ||"),
    ("extraPolls < kMaxSamePresentMapExtraPolls", "true"),
    ("elapsedTicks < frequencyTicks / kSamePresentMapBudgetDivisor", "true"),
):
    mutant = HDR.replace(old, new, 1)
    assert mutant != HDR and not integrated(SRC, mutant), old
assert "python tools/test_dx11_readback_map_00745.py" in WF
assert "tools/dx11_readback_map_probe_00745.cpp" in WF
print("00745 native full-frame Map failure fallback/quarantine PASS")
