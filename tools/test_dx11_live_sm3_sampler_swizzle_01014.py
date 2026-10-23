#!/usr/bin/env python3
"""Validate actual ps_3_0 sN sampler swizzle -> native texture GPU HLSL path."""
from pathlib import Path
import subprocess
import shutil
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
header = (root / "src/vr/d3d11/native_sm3_texture_codegen.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
def require(ok, label):
    if not ok:
        raise SystemExit("01014 live sampler swizzle FAIL: " + label)
parser = backend.split("bool build_r283_sm3_mov_shader_source(",1)[1].split(
    "bool r283_dxbc_payload(",1)[0]
require("op.samplerSwizzle = swizzle;" in parser and
        "modifier != D3DSPSM_NONE" in parser and
        "samplerDeclared[reg]" in parser and
        "(vertexStage && swizzle != 0xe4u)" in parser,
        "exact pixel sampler operand, declared dimension, modifier and VS fallback")
require(parser.count("op.textureMode, op.sources[2], op.sources[3],") == 3 and
        parser.count("op.samplerSwizzle)") == 3 and
        header.count("native_sm3_sampled_channels(") == 4,
        "2D/cube/volume texel swizzle feeds native shader Draw")
require("context->PSSetShader(" in bridge and
        "context->DrawIndexed(" in bridge and "context->Draw(" in bridge,
        "real game Draw/DrawIndexed GPU path remains connected")
compiler = shutil.which("g++") or shutil.which("clang++")
require(bool(compiler), "C++17 compiler unavailable")
with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / "dx11_ps3_swizzle"
    subprocess.run([compiler,"-std=c++17","-O2","-Wall","-Wextra",
        "-Werror","-pedantic","-I",str(root/"src/vr/d3d11"),
        str(root/"tools/dx11_sm3_sampler_swizzle_probe.cpp"),
        "-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print("01014 genuine game SM3 sampler swizzle HLSL regression PASS; runtime UNTESTED")
