#!/usr/bin/env python3
"""Native menu/car/race SM3 masked register arithmetic source -> GPU shader contract."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
shader = (root / "src/vr/d3d11/native_sm3_arithmetic_codegen.hpp").read_text()
probe = (root / "tools/dx11_sm3_arithmetic_codegen_probe.cpp").read_text()
def require(ok, message):
    if not ok:
        raise SystemExit("01011 masked SM3 game draw FAIL: " + message)
require("emitMaskedLanes" in shader and "mask & (1u << lane)" in shader,
        "game shader masked scalar source emission")
require("R283_D3D9_SM3_REGISTER_ARITHMETIC_TEXTURE2D_MATRIX_IFC_HLSL_MATERIALIZER_V12" in backend,
        "invalidate prior HLSL cache identity")
compiler = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
require("append_native_sm3_arithmetic(" in compiler and
        "op.destinationMask" in compiler and "op.sources[0]" in compiler,
        "real D3D9 bytecode -> masked HLSL codegen path")
draw = bridge.split("bool submit_live_sm3_game_draw(", 1)[1].split(
    "// Reuse geometric growth buffers", 1)[0]
require("context->DrawIndexed(" in draw and "context->Draw(" in draw and
        "context->PSSetShader(" in draw,
        "real native GPU draw path remains wired")
require("ddx((input.r0.xyzw).x)" in probe,
        "update existing arithmetic probe for channel-accurate derivatives")
cxx = shutil.which("g++") or shutil.which("clang++")
require(cxx is not None, "portable C++ compiler unavailable")
with tempfile.TemporaryDirectory() as temp:
    for name, source in [
        ("masked", "tools/dx11_live_sm3_masked_channels_01011.cpp"),
        ("arithmetic", "tools/dx11_sm3_arithmetic_codegen_probe.cpp"),
    ]:
        out = Path(temp) / name
        subprocess.run([cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                        "-pedantic", "-I", str(root / "src/vr/d3d11"),
                        str(root / source), "-o", str(out)], check=True)
        subprocess.run([str(out)], check=True)
print("01011 real shader masked partial-channel native emission PASS; game/HMD UNTESTED")
