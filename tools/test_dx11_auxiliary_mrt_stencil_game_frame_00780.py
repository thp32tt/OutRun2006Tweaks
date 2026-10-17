#!/usr/bin/env python3
"""00780 full-size game Draw/Clear: isolated writable MRT, stencil and D3D9 fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
offscreen = (root / "src/vr/d3d11/native_game_offscreen_pass.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
draw = bridge.split("bool isolated_offscreen_game_draw(", 1)[1].split(
    "bool proven_game_draw_no_target_writes(", 1)[0]
clear = bridge.split("bool preserve_offscreen_color_only_clear(", 1)[1].split(
    "void observe_game_surface_mutation(", 1)[0]

def implemented(d, c, h):
    return all((
        "if (hr == D3DERR_NOTFOUND) continue;" in d,
        "inactive_extra_mrt(maskKnown, mask)" in d,
        "SUCCEEDED(extra.As(&extraIdentity))" in d,
        "distinct_auxiliary_mrt(" in d,
        "reinterpret_cast<std::uintptr_t>(backbufferIdentity.Get())" in d,
        "stencilWrites && s.clearColor.mainDepthIdentity != 0u" in d,
        "GetDepthStencilSurface(boundDepth.GetAddressOf())" in d,
        "isolated_auxiliary_stencil_write(" in d,
        "isolated && stencilWrites && isolatedDepthWrite" in d,
        "s.clearColor.note_auxiliary_depth_write();" in d,
        "if ((flags & D3DCLEAR_TARGET) != 0u)" in c,
        "GetRenderTarget(slot, extra.GetAddressOf())" in c,
        "if (hr == D3DERR_NOTFOUND) continue;" in c,
        "FAILED(extra.As(&extraIdentity))" in c,
        "distinct_auxiliary_mrt(" in c,
        "s.clearColor.backbufferIdentity" in c,
        "GetDepthStencilSurface(depth.GetAddressOf())" in c,
        "return bound != 0u && mainBackbuffer != 0u &&" in h,
        "bound != mainBackbuffer;" in h,
        "maskKnown && writeMask != 0u &&" in h,
        "provenAuxiliaryDepth;" in h,
    ))
assert implemented(draw, clear, offscreen)
for scope, original, replacement in (
    ("draw", "SUCCEEDED(extra.As(&extraIdentity))", "true /* unverified MRT */"),
    ("draw", "distinct_auxiliary_mrt(", "inactive_extra_mrt("),
    ("draw", "stencilWrites && s.clearColor.mainDepthIdentity != 0u", "false"),
    ("draw", "isolated_auxiliary_stencil_write(", "no_main_stencil_write("),
    ("draw", "isolated && stencilWrites && isolatedDepthWrite", "false"),
    ("clear", "if ((flags & D3DCLEAR_TARGET) != 0u)", "if (false)"),
    ("clear", "FAILED(extra.As(&extraIdentity))", "false /* unverified alias */"),
    ("clear", "s.clearColor.backbufferIdentity", "0u /* missed main */"),
    ("header", "bound != mainBackbuffer;", "true; /* allowed alias */"),
    ("header", "maskKnown && writeMask != 0u &&\n            provenAuxiliaryDepth;", "true; /* main Z write */"),
):
    d, c, h = draw, clear, offscreen
    if scope == "draw": d = d.replace(original, replacement, 1)
    if scope == "clear": c = c.replace(original, replacement, 1)
    if scope == "header": h = h.replace(original, replacement, 1)
    assert not implemented(d, c, h), original
assert "tools/test_dx11_auxiliary_mrt_stencil_game_frame_00780.py" in workflow
assert "tools/dx11_auxiliary_mrt_stencil_game_frame_00780.cpp" in workflow
print("00780 native game auxiliary MRT/stencil Draw+Clear continuation and fallback PASS")
