#!/usr/bin/env python3
"""00779: live game offscreen stencil-test and masked MRT Draw integration."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/native_game_offscreen_pass.hpp").read_text(encoding="utf-8")
clear = (root / "src/vr/d3d11/native_game_clear_color.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
offscreen = bridge.split("bool isolated_offscreen_game_draw(", 1)[1].split(
    "bool proven_game_draw_no_target_writes(", 1)[0]
def integrated(b, h, c):
    return all((
        "GetRenderState(D3DRS_STENCILENABLE, &stencilEnabled)" in b,
        "GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)" in b,
        "if (!stencilMaskKnown) return false;" in b,
        "D3DRS_COLORWRITEENABLE1, D3DRS_COLORWRITEENABLE2" in b,
        "D3DRS_COLORWRITEENABLE3" in b,
        "GetRenderTarget(i, extra.GetAddressOf())" in b,
        "if (hr == D3DERR_NOTFOUND) continue;" in b,
        "GetRenderState(extraColorMasks[i - 1u], &mask)" in b,
        "no_main_stencil_write(" in b,
        "inactive_extra_mrt(maskKnown, mask)" in b,
        "noExtraRenderTargets, s.frameBatch.stopped" in b,
        "if (isolated && depthWrites && isolatedDepthWrite)" in b,
        "source_has_no_main_writes(" in b,
        "return !stencilEnabled || (maskKnown && writeMask == 0u)" in h,
        "return maskKnown && writeMask == 0u;" in h,
        "auxiliaryDepthCleared = false;" in c,
    ))
assert integrated(offscreen, header, clear)
for original, replacement in (
    ("GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)",
     "GetRenderState(D3DRS_STENCILENABLE, &stencilWriteMask)"),
    ("if (!stencilMaskKnown) return false;", "/* ignore unknown stencil mask */"),
    ("if (hr == D3DERR_NOTFOUND) continue;", "if (SUCCEEDED(hr)) continue;"),
    ("GetRenderState(extraColorMasks[i - 1u], &mask)",
     "GetRenderState(D3DRS_COLORWRITEENABLE, &mask)"),
    ("inactive_extra_mrt(maskKnown, mask)", "inactive_extra_mrt(true, 0u)"),
    ("no_main_stencil_write(", "allow_stencil_writes("),
    ("noExtraRenderTargets, s.frameBatch.stopped", "true, s.frameBatch.stopped"),
):
    assert original in offscreen, original
    assert not integrated(offscreen.replace(original, replacement, 1),
                          header, clear), original
assert "GetRenderTarget(slot, extra.GetAddressOf())" in bridge.split(
    "bool preserve_offscreen_color_only_clear(", 1)[1].split(
    "void observe_scene_boundary(", 1)[0]  # Clear ignores MRT write masks.
assert "tools/test_dx11_offscreen_masked_mrt_stencil_00779.py" in workflow
assert "tools/dx11_offscreen_masked_mrt_stencil_00779.cpp" in workflow
print("00779 full-size native menu/car/race masked MRT+read-only stencil PASS")
