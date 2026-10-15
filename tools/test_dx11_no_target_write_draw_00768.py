#!/usr/bin/env python3
"""00768: real game pixel-neutral Draw/Indexed -> full-frame continuation, fail-closed."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/native_game_masked_draw.hpp").read_text(encoding="utf-8")
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
probe = root / "tools/dx11_no_target_write_draw_probe_00768.cpp"

def linked(source: str) -> bool:
    draw = source.split("void observe(IDirect3DDevice9* game,", 1)[-1].split(
        "} // namespace", 1)[0]
    helper = source.split("bool proven_game_draw_no_target_writes(", 1)[-1].split(
        "void observe(IDirect3DDevice9* game,", 1)[0]
    unavailable = source.split("void observe_unavailable_game_draw(", 1)[-1].split(
        "void observe_failed_game_draw(", 1)[0]
    return all((
        "if (fullMode && proven_game_draw_no_target_writes(game, s))" in draw,
        "if (fullMode && proven_game_draw_no_target_writes(game, s))" in unavailable,
        "s.frameBatch.absorb_empty_source_draw(" in unavailable,
        "s.frameBatch.absorb_empty_source_draw(" in draw,
        "sourceOrdinal, sameSourceFullClear" in draw,
        "GameNativeMaskedDraw::no_target_write_source_draw(" in helper,
        "D3DRS_COLORWRITEENABLE" in helper,
        "D3DRS_ZWRITEENABLE" in helper,
        "D3DRS_STENCILENABLE" in helper,
        "status != D3DERR_NOTFOUND" in helper,
        "s.clearColor.matches(" in helper,
    ))

def unavailable_scissor_linked(source: str) -> bool:
    part = source.split("void observe_unavailable_game_draw(", 1)[-1].split(
        "void observe_failed_game_draw(", 1)[0]
    scissor = part.split("if (fullMode && isolated_offscreen_game_draw(", 1)[0]
    tokens = (
        "if (fullMode) {",
        "GetRenderState(D3DRS_SCISSORTESTENABLE,",
        "scissorEnabled == TRUE",
        "SUCCEEDED(game->GetViewport(&sourceViewport))",
        "SUCCEEDED(game->GetScissorRect(&sourceScissor))",
        "GameNativeScissorClip::excludes_viewport(",
        "s.frameBatch.absorb_empty_source_draw(",
        "sourceOrdinal, sameSourceFullClear",
        "s.frameBatch.abort();",
        "return;",
    )
    cursor = 0
    for token in tokens:
        position = scissor.find(token, cursor)
        if position < 0:
            return False
        cursor = position + len(token)
    return "s.clearColor.sourceDevice ==" in scissor

assert unavailable_scissor_linked(bridge), (
    "missing VB/IB fully clipped DrawIndexed must preserve native source ordinal")
head, tail = bridge.split("void observe_unavailable_game_draw(", 1)
for old, new in (
    ("scissorEnabled == TRUE", "scissorEnabled == FALSE"),
    ("GameNativeScissorClip::excludes_viewport(",
     "false && GameNativeScissorClip::excludes_viewport("),
    ("sourceOrdinal, sameSourceFullClear",
     "sourceOrdinal + 1u, sameSourceFullClear"),
):
    mutated = tail.replace(old, new, 1)
    assert mutated != tail and not unavailable_scissor_linked(
        head + "void observe_unavailable_game_draw(" + mutated), old

assert linked(bridge), "real game Draw/Indexed no-write continuity missing"
assert not linked(bridge.replace(
    "if (fullMode && proven_game_draw_no_target_writes(game, s))",
    "if (false && proven_game_draw_no_target_writes(game, s))"))
assert not linked(bridge.replace(
    "status != D3DERR_NOTFOUND", "false"))
assert not linked(bridge.replace(
    "s.clearColor.matches(", "bypassed_clear("))
assert "python tools/test_dx11_no_target_write_draw_00768.py" in workflow

cxx = shutil.which("g++") or shutil.which("clang++")
assert cxx, "portable C++17 compiler required"
with TemporaryDirectory(prefix="dx11-no-write-source-") as tmp:
    dst = Path(tmp)
    (dst / "tools").mkdir()
    (dst / "src/vr/d3d11").mkdir(parents=True)
    for filename in ("native_game_masked_draw.hpp", "native_game_frame_batch.hpp",
                     "native_game_scissor_clip.hpp"):
        shutil.copyfile(root / "src/vr/d3d11" / filename,
                        dst / "src/vr/d3d11" / filename)
    shutil.copyfile(probe, dst / "tools" / probe.name)
    output = dst / "no_write_source_probe"
    cmd = [cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
           "-pedantic", str(dst / "tools" / probe.name), "-o", str(output)]
    subprocess.run(cmd, check=True, capture_output=True)
    subprocess.run([str(output)], check=True, capture_output=True)
    hdr = dst / "src/vr/d3d11/native_game_masked_draw.hpp"
    hdr.write_text(header.replace(
        "clearedGameBackbuffer && colorMask == 0u",
        "clearedGameBackbuffer && colorMask != 0u"), encoding="utf-8")
    assert subprocess.run(cmd, capture_output=True).returncode != 0, (
        "destructively permitting color writes must fail C++ source tests")
print("00768 menu/car/race Draw and DrawIndexed no-write stream + D3D9 fallback PASS")
