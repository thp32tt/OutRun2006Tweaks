#!/usr/bin/env python3
"""00743 native menu/car/race full-frame staging ring integration regression."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HEADER = (ROOT / "src/vr/d3d11/native_game_frame_publication.hpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")


def integrated(source: str, header: str) -> bool:
    start = source.find("void before_game_present(")
    end = source.find("void before_game_reset(", start)
    if start < 0 or end < start:
        return False
    body = source[start:end]
    stale = body.find("for (auto& prior : s.readbacks)")
    mask = body.find("std::uint32_t occupiedSlots = 0u;", stale)
    select = body.find("GameNativeFramePublication::select_available_slot(", mask)
    admission = body.find("if (availableSlot < kReadbackSlots)", select)
    copy = body.find("ctx->CopyResource(next.staging.Get(), s.backend.color_texture())", admission)
    fence = body.find("ctx->End(next.fence.Get())", copy)
    publish = body.find("auto& oldest = s.readbacks[fullMode ? fullSlot : s.readSlot]", fence)
    return all((
        0 <= stale < mask < select < admission < copy < fence < publish,
        "if (s.readbacks[i].busy) occupiedSlots |= (1u << i);" in body[mask:select],
        "fullSlot = availableSlot;" in body[admission:copy],
        "s.writeSlot = (fullSlot + 1u) % kReadbackSlots;" in body[fence:publish],
        "++s.droppedCopies;" in body[fence:publish],
        "if (oldest.busy && !oldest.quarantined &&" in body[publish:],
        "oldest.provenance.may_present(s.presents, fullMode)" in body,
        "return slotCount;" in header,
        "(occupiedMask & (1u << slot)) == 0u" in header,
        "if (slotCount == 0u || slotCount > 32u || preferred >= slotCount)" in header,
    ))


assert integrated(SOURCE, HEADER), "Native full-frame ring selection must preserve same-Present fallback"
for old, new in (
    ("fullSlot = availableSlot;", "fullSlot = s.writeSlot;"),
    ("if (availableSlot < kReadbackSlots)", "if (availableSlot <= kReadbackSlots)"),
    ("if (s.readbacks[i].busy) occupiedSlots", "if (!s.readbacks[i].busy) occupiedSlots"),
    ("s.writeSlot = (fullSlot + 1u) % kReadbackSlots;", "s.writeSlot = (s.writeSlot + 1u) % kReadbackSlots;"),
    ("if (oldest.busy && !oldest.quarantined &&", "if (oldest.busy)"),
):
    mutant = SOURCE.replace(old, new, 1)
    assert mutant != SOURCE and not integrated(mutant, HEADER), old
for old, new in (
    ("(occupiedMask & (1u << slot)) == 0u", "(occupiedMask & (1u << slot)) != 0u"),
    ("preferred >= slotCount", "preferred > slotCount"),
):
    mutant = HEADER.replace(old, new, 1)
    assert mutant != HEADER and not integrated(SOURCE, mutant), old
assert "python tools/test_dx11_full_frame_slot_reuse_00743.py" in WF
assert "tools/dx11_full_frame_slot_reuse_probe_00743.cpp" in WF
print("00743 native full-frame busy-slot recovery + input-safe fallback PASS")
