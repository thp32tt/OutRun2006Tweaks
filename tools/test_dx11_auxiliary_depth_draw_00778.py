#!/usr/bin/env python3
"""00778: real D3D9 offscreen depth-writing game Draw keeps native frame contiguous."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/native_game_offscreen_pass.hpp").read_text(encoding="utf-8")
clear = (root / "src/vr/d3d11/native_game_clear_color.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
offscreen = bridge.split("bool isolated_offscreen_game_draw(", 1)[1].split(
    "bool proven_game_draw_no_target_writes(", 1)[0]
normal = bridge.split("void observe(IDirect3DDevice9* game,", 1)[1].split(
    "bool preserve_offscreen_color_only_clear(", 1)[0]
unavailable = bridge.split("void observe_unavailable_game_draw(", 1)[1].split(
    "void observe_failed_game_draw(", 1)[0]
def integrated(source, depth):
    return all((
        "depthWrites = zEnabled != D3DZB_FALSE && zWriteEnabled != FALSE" in source,
        "depthWrites && s.clearColor.mainDepthIdentity != 0u" in source,
        "GetDepthStencilSurface(boundDepth.GetAddressOf())" in source,
        "boundDepth.As(&depthIdentity)" in source,
        "isolatedDepthWrite = !s.clearColor.main_depth_still_bound(" in source,
        "targetIdentity.Get() != backbufferIdentity.Get()" in source,
        "no_main_depth_write(" in source and "isolatedDepthWrite)" in source,
        "no_main_stencil_write(" in source,
        "stencilEnabled != FALSE, stencilMaskKnown, stencilWriteMask)" in source,
        "noExtraRenderTargets, s.frameBatch.stopped" in source,
        "if (isolated && depthWrites && isolatedDepthWrite)" in source,
        "if (isolated && depthWrites && isolatedDepthWrite)\n        s.clearColor.note_auxiliary_depth_write()" in source,
        "void note_auxiliary_depth_write()" in clear,
        "provenAuxiliaryDepth = false" in depth,
        "!depthEnabled || !depthWritesEnabled || provenAuxiliaryDepth" in depth,
    ))
assert integrated(offscreen, header)
assert "GameNativeClearColor" in clear
assert "isolated_offscreen_game_draw(game, s)" in normal
assert "isolated_offscreen_game_draw(game, s)" in unavailable
assert "s.frameBatch.absorb_empty_source_draw(" in normal
assert "s.frameBatch.absorb_empty_source_draw(" in unavailable
for original, fake in (
    ("depthWrites && s.clearColor.mainDepthIdentity != 0u", "depthWrites"),
    ("GetDepthStencilSurface(boundDepth.GetAddressOf())", "GetDepthStencilSurface(nullptr)"),
    ("boundDepth.As(&depthIdentity)", "boundDepth.As(nullptr)"),
    ("isolatedDepthWrite = !s.clearColor.main_depth_still_bound(",
     "isolatedDepthWrite = s.clearColor.main_depth_still_bound("),
    ("GameNativeOffscreenPass::no_main_stencil_write(", "GameNativeOffscreenPass::unproved_stencil_writes("),
    ("s.clearColor.note_auxiliary_depth_write()", "/* missed auxiliary Z write */"),
    ("targetIdentity.Get() != backbufferIdentity.Get()", "true /* unsafe target alias */"),
):
    assert not integrated(offscreen.replace(original, fake, 1), header), original
assert not integrated(offscreen, header.replace(
    "|| provenAuxiliaryDepth", "&& provenAuxiliaryDepth", 1))
assert "tools/test_dx11_auxiliary_depth_draw_00778.py" in workflow
assert "tools/dx11_auxiliary_depth_draw_00778.cpp" in workflow
print("00778 native menu/vehicle/race offscreen depth Draw and fallback PASS")
