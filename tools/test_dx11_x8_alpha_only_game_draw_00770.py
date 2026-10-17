#!/usr/bin/env python3
"""00770 X8 alpha-only real game Draw/DrawIndexed continuity and safe A8 fallback."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/native_game_masked_draw.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def connected(source, masked):
    helper = source.split("bool proven_game_draw_no_target_writes(", 1)[-1].split(
        "void observe(IDirect3DDevice9* game,", 1)[0]
    draw = source.split("void observe(IDirect3DDevice9* game,", 1)[-1].split(
        "} // namespace", 1)[0]
    unavailable = source.split("void observe_unavailable_game_draw(", 1)[-1].split(
        "void observe_failed_game_draw(", 1)[0]
    return all((
        "GameNativeMaskedDraw::no_visible_target_write_source_draw(" in helper,
        "backbufferDesc.Format == D3DFMT_A8R8G8B8" in helper,
        "backbufferDesc.Format != D3DFMT_X8R8G8B8" in helper,
        "targetIdentity.Get() != identity.Get()" in helper,
        "GetRenderTarget(0, target.GetAddressOf())" in helper,
        "status != D3DERR_NOTFOUND" in helper,
        "GetRenderState(D3DRS_STENCILWRITEMASK," in helper,
        "const bool stencilReadOnly = game_stencil_is_read_only(" in helper,
        "stencilEnabled, stencilMaskKnown, stencilWriteMask" in helper,
        "if (!stencilReadOnly) return false;" in helper,
        "stencilWrites, false" in helper,
        "GameNativeOffscreenPass::inactive_extra_mrt(true, extraMask)" in helper,
        "s.clearColor.matches(" in helper,
        "if (fullMode && proven_game_draw_no_target_writes(game, s))" in draw,
        "if (fullMode && proven_game_draw_no_target_writes(game, s))" in unavailable,
        "s.frameBatch.absorb_empty_source_draw(" in draw,
        "s.frameBatch.absorb_empty_source_draw(" in unavailable,
        "no_target_write_source_draw(" in masked,
        "effective_native_mask(d3d9Mask, targetHasAlpha)" in masked,
        "(d3d9Mask & ~kLegalChannels) == 0u" in masked,
    ))

assert connected(bridge, header), "X8 alpha-only game Draw/Indexed source linkage missing"
head, tail = bridge.split("bool proven_game_draw_no_target_writes(", 1)
for old, new in (
    ("targetIdentity.Get() != identity.Get()", "false"),
    ("backbufferDesc.Format == D3DFMT_A8R8G8B8", "true"),
    ("status != D3DERR_NOTFOUND", "false"),
    ("s.clearColor.matches(", "true /* no-clear */ ("),
):
    assert old in tail and not connected(
        head + "bool proven_game_draw_no_target_writes(" + tail.replace(old, new, 1),
        header), old
assert not connected(bridge.replace(
    "if (!stencilReadOnly) return false;", "if (false) return false;"), header)
assert not connected(bridge.replace(
    "if (fullMode && proven_game_draw_no_target_writes(game, s))",
    "if (false && proven_game_draw_no_target_writes(game, s))", 1), header)
assert "python tools/test_dx11_x8_alpha_only_game_draw_00770.py" in workflow
compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "portable C++17 compiler required"
with TemporaryDirectory(prefix="dx11-x8-alpha-draw-") as tmp:
    base = Path(tmp)
    (base / "src/vr/d3d11").mkdir(parents=True)
    (base / "tools").mkdir()
    for name in ("native_game_masked_draw.hpp", "native_game_frame_batch.hpp"):
        shutil.copyfile(root / "src/vr/d3d11" / name, base / "src/vr/d3d11" / name)
    shutil.copyfile(root / "tools/dx11_x8_alpha_only_game_draw_00770.cpp",
                    base / "tools/dx11_x8_alpha_only_game_draw_00770.cpp")
    exe = base / "x8_draw"
    command = [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
               "-pedantic", "-O2",
               str(base / "tools/dx11_x8_alpha_only_game_draw_00770.cpp"),
               "-o", str(exe)]
    subprocess.run(command, check=True, capture_output=True)
    subprocess.run([str(exe)], check=True, capture_output=True)
    hdr = base / "src/vr/d3d11/native_game_masked_draw.hpp"
    hdr.write_text(header.replace(
        "(d3d9Mask & ~kLegalChannels) == 0u",
        "(d3d9Mask & ~kLegalChannels) != 0u"), encoding="utf-8")
    assert subprocess.run(command, capture_output=True).returncode != 0, (
        "invalid D3D9 mask mutation must be rejected by C++ assertions")
print("00770 X8-alpha-only actual menu/vehicle/race Draw/Indexed and A8 fallback PASS")
