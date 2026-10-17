#!/usr/bin/env python3
"""00744 full game frame readback invalid GPU fence quarantine regression."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HEADER = (ROOT / "src/vr/d3d11/native_game_frame_publication.hpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")


def integrated(source: str, header: str) -> bool:
    begin = source.find("void before_game_present(")
    end = source.find("void before_game_reset(", begin)
    if begin < 0 or end < begin:
        return False
    body = source[begin:end]
    first = body.find("for (auto& prior : s.readbacks)")
    source_check = body.find("prior.quarantined ||", first)
    fence_query = body.find("const HRESULT done = ctx->GetData", source_check)
    classify = body.find("GameNativeFramePublication::classify_fence(", fence_query)
    completed = body.find("if (fenceResult == GameNativeReadbackFence::Complete)", classify)
    retire = body.find("prior.busy = false;", completed)
    fail = body.find("fenceResult == GameNativeReadbackFence::Failed", retire)
    quarantine = body.find("prior.quarantined = true;", fail)
    select = body.find("if (s.readbacks[i].busy) occupiedSlots", quarantine)
    full_poll = body.find("if (oldest.busy && !oldest.quarantined", select)
    failed_now = body.find("GameNativeReadbackFence::Failed", full_poll)
    quarantine_now = body.find("oldest.quarantined = true;", failed_now)
    return all((
        0 <= first < source_check < fence_query < classify < completed <
        retire < fail < quarantine < select < full_poll < failed_now < quarantine_now,
        "bool quarantined = false;" in source,
        source.count("item.quarantined = false;") == 2,
        "oldest.busy = false;" not in body[failed_now:quarantine_now + 80],
        "result == 0 ? GameNativeReadbackFence::Complete" in header,
        "result == 1 ? GameNativeReadbackFence::Pending" in header,
        "GameNativeReadbackFence::Failed" in header,
    ))


assert integrated(SOURCE, HEADER), "Failed EVENT queries must not release in-flight game frame staging"
for old, new in (
    ("if (fenceResult == GameNativeReadbackFence::Complete)",
     "if (fenceResult != GameNativeReadbackFence::Pending)"),
    ("prior.quarantined = true;", "prior.busy = false;"),
    ("if (oldest.busy && !oldest.quarantined", "if (oldest.busy && oldest.quarantined"),
    ("oldest.quarantined = true;", "oldest.busy = false;"),
    ("prior.quarantined ||", "false ||"),
):
    # 00745/00746 add earlier map-failure quarantine paths for both
    # the current and previously pending slots. Mutate the LAST matching
    # site to test this legacy EVENT-failure-specific branch.
    if old in ("oldest.quarantined = true;", "prior.quarantined = true;"):
        at = SOURCE.rfind(old)
        assert at >= 0, old
        mutant = SOURCE[:at] + new + SOURCE[at + len(old):]
    else:
        mutant = SOURCE.replace(old, new, 1)
    assert mutant != SOURCE and not integrated(mutant, HEADER), old
for old, new in (
    ("result == 0 ? GameNativeReadbackFence::Complete",
     "result != 1 ? GameNativeReadbackFence::Complete"),
    ("result == 1 ? GameNativeReadbackFence::Pending",
     "result != 1 ? GameNativeReadbackFence::Pending"),
):
    mutant = HEADER.replace(old, new, 1)
    assert mutant != HEADER and not integrated(SOURCE, mutant), old
assert "python tools/test_dx11_readback_quarantine_00744.py" in WF
assert "tools/dx11_readback_quarantine_probe_00744.cpp" in WF
print("00744 full frame GPU-fence quarantine and D3D9 input fallback PASS")
