#!/usr/bin/env python3
"""00764 real menu/vehicle/race fully clipped Draw stream continuity."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/native_game_scissor_clip.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
def wired(src, predicate):
    if '#include "native_game_scissor_clip.hpp"' not in src:
        return False
    if "void observe(IDirect3DDevice9* game," not in src:
        return False
    body = src.split("void observe(IDirect3DDevice9* game,", 1)[1]
    body = body.split("bool preserve_offscreen_color_only_clear(", 1)[0]
    sequence = [
        "if (!game_native_primitive_element_count(",
        "if (fullMode) {",
        "GetRenderState(D3DRS_SCISSORTESTENABLE, &scissorEnabled)",
        "scissorEnabled == TRUE",
        "SUCCEEDED(game->GetViewport(&sourceViewport))",
        "SUCCEEDED(game->GetScissorRect(&sourceScissor))",
        "GameNativeScissorClip::excludes_viewport(",
        "s.frameBatch.absorb_empty_source_draw(",
        "s.frameBatch.abort();",
        "return;",
        "if (!supported_game_state("
    ]
    positions = [body.find(s) for s in sequence]
    if not all(p >= 0 for p in positions) or positions != sorted(positions):
        return False
    return all(t in predicate for t in (
        "viewportWidth == 0u || viewportHeight == 0u",
        "scissorRight <= scissorLeft || scissorBottom <= scissorTop",
        "scissorRight <= static_cast<std::int64_t>(viewportX)",
        "scissorLeft >= viewportRight",
        "scissorBottom <= static_cast<std::int64_t>(viewportY)",
        "scissorTop >= viewportBottom",
    )) and "sameSourceFullClear" in body
assert wired(bridge,header), "scissor no-op Draw/DrawIndexed path not connected"
for old,new in (
    ("scissorEnabled == TRUE", "scissorEnabled == FALSE"),
    ("GameNativeScissorClip::excludes_viewport(", "false /* skip scissor */ && GameNativeScissorClip::excludes_viewport("),
    ("s.frameBatch.absorb_empty_source_draw(", "false /* source ordinal not preserved */ && s.frameBatch.absorb_empty_source_draw("),
):
    bad = bridge.replace(old,new,1)
    assert bad != bridge and not wired(bad,header), old
assert "tools/test_dx11_game_clipped_draw_00764.py" in workflow
assert "tools/dx11_game_clipped_draw_00764.cpp" in workflow
print("00764 full-game clipped Draw/DrawIndexed continuity and fail-closed D3D9 PASS")
