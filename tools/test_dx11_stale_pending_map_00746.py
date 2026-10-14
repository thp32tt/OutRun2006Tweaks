#!/usr/bin/env python3
"""00746: a delayed D3D11 Map cannot release/repaint a full game staging slot."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")


def integrated(source: str) -> bool:
    first = source.find("void before_game_present(")
    last = source.find("void before_game_reset(", first)
    if first < 0 or last <= first:
        return False
    body = source[first:last]
    stale_start = body.find("for (auto& prior : s.readbacks)")
    stale_end = body.find("if (complete && outputWritable &&", stale_start)
    if not 0 <= stale_start < stale_end:
        return False
    stale = body[stale_start:stale_end]
    check = stale.find("if (prior.mapPending)")
    mapping = stale.find("ctx->Map(", check)
    classification = stale.find("GameNativeFramePublication::classify_map(", mapping)
    approved = stale.find("if (staleResult == GameNativeReadbackMap::Ready)", classification)
    unmap = stale.find("ctx->Unmap(prior.staging.Get(), 0);", approved)
    ownership = stale.find("prior.mapPending = false;", unmap)
    recycle = stale.find("prior.busy = false;", ownership)
    error = stale.find("staleResult == GameNativeReadbackMap::Failed", recycle)
    quarantine = stale.find("prior.quarantined = true;", error)
    old_fence_failure = stale.find("fenceResult == GameNativeReadbackFence::Failed", quarantine)
    new_map = body.find("if (mapResult == GameNativeReadbackMap::Ready)")
    pending = body.find("} else if (mapResult == GameNativeReadbackMap::Pending)", new_map)
    pending_retained = body.find("oldest.mapPending = true;", pending)
    map_failure = body.find("} else if (mapResult == GameNativeReadbackMap::Failed)", pending_retained)
    return all((
        0 <= check < mapping < classification < approved < unmap <
        ownership < recycle < error < quarantine < old_fence_failure,
        0 <= new_map < pending < pending_retained < map_failure,
        "D3D11_MAP_FLAG_DO_NOT_WAIT" in stale[mapping:classification],
        "staleMap.pData != nullptr" in stale[classification:approved],
        "staleResult == GameNativeReadbackMap::Pending" not in
            stale[approved:quarantine],
        "oldest.busy = false;" not in body[pending:map_failure],
        "bool mapPending = false;" in source,
        source.count("item.mapPending = false;") == 2,
        "next.mapPending = false;" in body,
        "if (!prior.busy || prior.quarantined ||" in stale,
        "if (oldest.busy && !oldest.quarantined &&" in body,
    ))


assert integrated(SRC), "pending full-frame Map must not recycle staging before Map/Unmap"
for old, new in (
    ("if (prior.mapPending)", "if (false)"),
    ("staleResult == GameNativeReadbackMap::Ready", "staleResult != GameNativeReadbackMap::Pending"),
    ("prior.mapPending = false;", "prior.mapPending = true;"),
    ("prior.quarantined = true;", "prior.busy = false;"),
    ("oldest.mapPending = true;", "oldest.busy = false;"),
    ("ctx->Unmap(prior.staging.Get(), 0);", "// BUG: stale CPU Map not released"),
    ("item.mapPending = false;", "item.mapPending = true;"),
):
    mutant = SRC.replace(old, new, 1)
    assert mutant != SRC and not integrated(mutant), old

assert "python tools/test_dx11_stale_pending_map_00746.py" in WF
print("00746 full frame pending CPU Map -> stale Map/Unmap -> safe slot recovery PASS")
