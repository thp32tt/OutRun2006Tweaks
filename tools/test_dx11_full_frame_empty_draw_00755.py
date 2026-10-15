#!/usr/bin/env python3
"""Game Draw -> native full-frame ordering; source-only, no Quest3 proof."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
batch = (root / "src/vr/d3d11/native_game_frame_batch.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
probe = (root / "tools/dx11_full_frame_empty_draw_probe_00755.cpp").read_text()

def integrated(b: str, h: str) -> bool:
    a = b.find("void observe(IDirect3DDevice9* game,")
    z = b.find("void observe_unavailable_game_draw(", a)
    failed = b.find("void observe_failed_game_draw(", z)
    present = b.find("void before_game_present(", failed)
    if min(a, z, failed, present) < 0: return False
    section = b[a:z]
    before_span = section.find("game_native_primitive_element_count(")
    consume = section.find("s.frameBatch.absorb_empty_source_draw(")
    valid_type = section.find("type >= D3DPT_POINTLIST && type <= D3DPT_TRIANGLEFAN")
    return (0 <= section.find("const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++")
            < valid_type < consume < before_span and
            "if (fullMode && primitives == 0u &&" in section and
            "sourceOrdinal, sameSourceFullClear))" in section and
            "s.clearColor.sourceDevice ==" in section and
            "s.frameBatch.abort();" in section[consume:before_span] and
            "s.frameBatch.abort();" in b[failed:present] and
            "if (!accepts_full(ordinal) ||" in h and
            "if (!sameSourceFullClear) return false;" in h and
            "std::uint32_t leadingEmptySourceDraws = 0u;" in h and
            "std::uint32_t postDrawEmptySourceDraws = 0u;" in h and
            "!accepts_source_draw(ordinal, true)" in h and
            "++postDrawEmptySourceDraws;" in h and
            "postDrawEmptySourceDraws = 0u;" in h and
            "++leadingEmptySourceDraws;" in h and
            "leadingEmptySourceDraws = 0u;" in h and
            "record_source_draw(ordinal);" in h and
            "accepts_full_on_source_target(" in h and
            "return matchesClearedBackbuffer &&" in h and
            "const bool sameClearedGameTarget = s.clearColor.matches(" in section and
            "s.frameBatch.accepts_full_on_source_target(" in section and
            "sourceOrdinal, sameClearedGameTarget)" in section)

assert integrated(bridge,batch), "empty game Draw must preserve source order only after actual native Draw"
for broken_bridge, broken_batch in (
    (bridge.replace("type >= D3DPT_POINTLIST && type <= D3DPT_TRIANGLEFAN",
                    "/* unchecked topology */", 1), batch),
    (bridge.replace("sourceOrdinal, sameSourceFullClear))",
                    "sourceOrdinal, /* missing clear proof */ false))", 1), batch),
    (bridge, batch.replace("if (!sameSourceFullClear) return false;",
                           "if (true) return false;", 1)),
    (bridge, batch.replace("++postDrawEmptySourceDraws; // source order only;",
                           "/* no post-GPU ordinal increment */ //", 1)),
    (bridge.replace("s.frameBatch.accepts_full_on_source_target(",
                    "s.frameBatch.accepts_full_seeded(", 1), batch),
    (bridge, batch.replace("return matchesClearedBackbuffer &&",
                           "return true &&", 1)),
):
    assert (broken_bridge != bridge or broken_batch != batch), "stale destructive replacement"
    assert not integrated(broken_bridge, broken_batch), "destructive control escaped"
assert "full_game_empty_draw_contract()" in probe
assert "leading_game_empty_draw_contract()" in probe
assert "full_game_target_continuity_contract()" in probe
assert "can_seed_pre_draw_depth(true, false)" in probe
assert "test_dx11_full_frame_empty_draw_00755.py" in workflow
assert "dx11_full_frame_empty_draw_probe_00755.cpp" in workflow
print("PASS 00755+00759: leading/post-game empty Draws preserve first GPU Draw, depth clear, full-frame source order and D3D9 fallback (static only)")
