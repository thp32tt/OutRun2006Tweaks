#!/usr/bin/env python3
"""00771 live Draw/Indexed diffuse-only TEXn source -> native PS and full Present."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess, shutil
root = Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
fvf=(root/"src/vr/d3d11/live_game_fvf_layout.hpp").read_text(encoding="utf-8")
workflow=(root/".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
def joined(b):
    state=b.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    decode=b.split("bool translate_vertices(",1)[1].split("bool mirror_texture(",1)[0]
    draw=b.split("void observe(IDirect3DDevice9* game,",1)[1].split("} // namespace",1)[0]
    submit=b.split("bool submit(State& s,",1)[1].split("void observe(",1)[0]
    return all((
        "game_fvf_diffuse_only_inactive_texture(" in state,
        "followingColorOp, layout.hasDiffuse" in state,
        "capture.enabled = layout.textured && !diffuseOnly;" in state,
        "capture.inactiveStage0TextureBypass = diffuseOnly && layout.textured;" in state,
        "else if (tex && !diffuseOnly)" in state,
        "capture.inactiveStage0TextureBypass" in decode,
        "game_fvf_decode_vertex(data, stride, layout, decoded)" in decode,
        "if (capture.enabled &&" in decode,
        "if (!supported_game_state(game, type, vp, layout, transforms, capture, output))" in draw,
        "translate_vertices(bytes, vertexCount, stride, vp," in draw,
        "if (!submit(s, vertices, indices, indexCount, type, capture, output))" in draw,
        "ctx->PSSetShader(capture.stage1Enabled ?" in submit,
        "!capture.enabled ? s.ps.Get()" in submit,
        "s.frameBatch.record_source_draw(sourceOrdinal);" in draw,
    ))
assert joined(bridge), "real-game source/geometry/shader/Draw/Indexed continuity disconnected"
assert "python tools/test_dx11_inactive_texture_game_frame_00771.py" in workflow
for old, replacement in (
    ("capture.enabled = layout.textured && !diffuseOnly;",
     "capture.enabled = layout.textured;"),
    ("else if (tex && !diffuseOnly)", "else if (tex)"),
    ("capture.inactiveStage0TextureBypass = diffuseOnly && layout.textured;",
     "capture.inactiveStage0TextureBypass = false;"),
    ("followingColorOp, layout.hasDiffuse", "followingColorOp, false"),
):
    assert old in bridge and not joined(bridge.replace(old,replacement,1)),old
assert "nextOp == 1u" in fvf
compiler=shutil.which("g++") or shutil.which("clang++")
assert compiler,"C++17 compiler required"
with TemporaryDirectory(prefix="dx11-live-inactive-") as d:
    out=Path(d)/"probe"
    cmd=[compiler,"-std=c++17","-O2","-Wall","-Wextra","-Werror",
         "-pedantic",str(root/"tools/dx11_inactive_texture_game_frame_00771.cpp"),
         "-o",str(out)]
    subprocess.run(cmd,check=True,capture_output=True)
    subprocess.run([str(out)],check=True,capture_output=True)
print("00771 native real menu/vehicle/race diffuse-only TEXn Draw/Indexed PASS")
