#!/usr/bin/env python3
"""Confirm clipped real D3D9 menu/race Clears seed native Draw/Indexed; negatives fall back."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
coverage = (root / "src/vr/d3d11/native_game_clear_coverage.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
batch = (root / "src/vr/d3d11/native_game_frame_batch.hpp").read_text()
hook = (root / "src/vr/d3d9/stereo_renderer.cpp").read_text()
probe = (root / "tools/dx11_full_clear_clipped_00762.cpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

def linked(h, b, d, r, p, w):
    color = b[b.index("void observe_game_clear("):b.index("void observe_unavailable_game_draw(")]
    depth = b[b.index("bool observe_game_depth_clear("):b.index("void observe_game_clear(")]
    draw = b[b.index("void observe(IDirect3DDevice9* game,"):b.index("} // namespace", b.index("void observe(IDirect3DDevice9* game,"))]
    clear = r[r.index("HRESULT __stdcall ClearDestR9("):r.index("template <typename ActualDraw, typename LegacyDraw>")]
    return all((
        "clipped[validCount++] = c;" in h,
        "if (c.x1 >= c.x2 || c.y1 >= c.y2) continue;" in h,
        "if (nextX == x) return false;" in h,
        "if (validCount == 0u) return false;" in h,
        "if (r.x1 >= r.x2 || r.y1 >= r.y2) return false;" in h,
        "GameNativeClearCoverage::covers_whole(" in color,
        "GameNativeClearCoverage::covers_whole(" in depth,
        "s.clearColor.record(sourceDevice," in color,
        "s.frameBatch.note_full_depth_clear(z);" in depth,
        "s.frameBatch.accepts_full_on_source_target(" in draw,
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in b,
        "observe_game_clear(" in clear,
        "observe_scene_boundary(device)" in clear,
        "batch.publishable_full(true,2u)" in p,
        "!full(oversize,1u)" not in p,
        "full(incomplete,2u)" in p,
        "full(badOrder,2u)" in p,
        "test_dx11_full_clear_clipped_00762.py" in w,
        "dx11_full_clear_clipped_00762.cpp" in w,
    ))
assert linked(coverage,bridge,batch,hook,probe,workflow)
for old,new in (
    ("clipped[validCount++] = c;", "/* clipped RT union disabled */"),
    ("if (nextX == x) return false;", "if (false) return false;"),
    ("if (validCount == 0u) return false;", "if (false) return false;"),
    ("if (r.x1 >= r.x2 || r.y1 >= r.y2) return false;", "if (false) return false;"),
):
    assert old in coverage and not linked(coverage.replace(old,new,1),bridge,batch,hook,probe,workflow)
assert not linked(coverage,bridge.replace("GameNativeClearCoverage::covers_whole(", "/* native full color clear removed */",1),batch,hook,probe,workflow)
assert not linked(coverage,bridge, batch.replace("return matchesClearedBackbuffer &&","return true &&",1),hook,probe,workflow) if "return matchesClearedBackbuffer &&" in batch else True
assert not linked(coverage,bridge,batch,hook.replace("observe_scene_boundary(device)","/* boundary bypass */",1),probe,workflow)
print("PASS 00762 clipped D3D9 whole-target color/depth Clear -> native full Draw/Indexed + fallback (source only)")
