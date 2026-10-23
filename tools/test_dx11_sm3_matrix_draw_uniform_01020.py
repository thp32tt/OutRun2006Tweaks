#!/usr/bin/env python3
"""Source-linked compiled regression for live SM3 matrix -> IFC native Draw."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
block = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
def require(ok, what):
    if not ok:
        raise SystemExit("01020 native matrix IFC regression FAIL: " + what)

require("matrixRowsAreAbsolute = !relative" in block and
        "native_sm3_relative_matrix_references(" in block and
        "native_sm3_const_reference(" in block,
        "real relative/absolute c# matrix row expansion must feed provenance")
require("native_sm3_matrix_draw_uniform(" in block and
        "tempDrawUniformity.write(" in block and
        "sourcesDrawUniform;" in block,
        "absolute uniform M*x* result must write physical TEMP provenance")
require("tempDrawUniformity.contains(reg, uniformPhysicalComponents)" in block and
        "native_sm3_ifc_is_quad_uniform(" in block and
        "derivativeUniformity.implicit_sampling_safe()" in block,
        "derived scalar TEMP must reach safe IFC/TEX derivative classifier")
require("append_native_sm3_matrix(" in block and
        "append_native_sm3_texture2d_sample(" in block and
        "context->PSSetShader(" in bridge and
        "context->DrawIndexed(" in bridge and "context->Draw(" in bridge,
        "matrix shader emission must remain linked to native game Draw")
require("structuredFlow.empty() && !op.predicated" in block and
        "op.opcode != NativeSm3ArithmeticOpcode::DerivativeX" in block,
        "conditional, predicated and derivative writes may not authorize IFC")
compiler = shutil.which("g++") or shutil.which("clang++")
require(compiler is not None, "no C++17 compiler")
with tempfile.TemporaryDirectory() as directory:
    binary = str(Path(directory) / "sm3_matrix_uniform")
    subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic",
                    str(root / "tools/dx11_sm3_matrix_draw_uniform_probe_01020.cpp"),
                    "-o", binary], check=True)
    subprocess.run([binary], check=True)
print("01020 SM3 live native matrix -> IFC/TEX compiled PASS; HMD UNTESTED")
