#!/usr/bin/env python3
"""Genuine game ps_3_0 TEXKILL xyz -> HLSL clip -> native Draw admission."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
shader = (root / "src/vr/d3d11/native_sm3_fragment_codegen.hpp").read_text()
def require(test, reason):
    if not test:
        raise SystemExit("01013 SM3 TEXKILL native draw FAIL: " + reason)
parser = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
require("case D3DSIO_TEXKILL:" in parser and
        "op.texkillWrittenMask = tempWritten[op.destinationRegister]" in parser and
        "native_sm3_texkill_ready(" in parser and
        "append_native_sm3_texkill(" in parser,
        "game shader source -> TEMP lane mask -> D3D11 pixel clip")
require("op.destinationType != D3DSPR_TEMP" in parser and
        "mask != 0x0fu" in parser,
        "unknown TEXKILL operands retain D3D9Ex Draw")
require("(priorWrittenMask & 0x07u) == 0x07u" in shader and
        "clip(r283_t" in shader and ".xyz" in shader,
        "reads only genuine xyz, never fabricated TEMP.w")
draw = bridge.split("bool submit_live_sm3_game_draw(", 1)[1].split(
    "// Reuse geometric growth buffers", 1)[0]
require("context->PSSetShader(" in draw and
        "context->DrawIndexed(" in draw and "context->Draw(" in draw,
        "live game Draw/DrawIndexed remains linked to GPU path")
compiler = shutil.which("g++") or shutil.which("clang++")
require(compiler is not None, "C++17 compiler unavailable")
with tempfile.TemporaryDirectory() as tmp:
    output = Path(tmp) / "texkill"
    subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic", "-I", str(root / "src/vr/d3d11"),
                    str(root / "tools/dx11_live_sm3_texkill_01013.cpp"),
                    "-o", str(output)], check=True)
    subprocess.run([str(output)], check=True)
print("01013 genuine game TEXKILL xyz native shader regression PASS; runtime UNTESTED")
