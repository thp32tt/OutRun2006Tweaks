#!/usr/bin/env python3
"""C++17/source-linked test for actual SM3 SETP predicated native game texture Draw."""
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
        raise SystemExit("01021 live native SETP/TEX regression FAIL: " + what)
require("NativeSm3DrawUniformPredicate predicateDrawUniformity;" in block and
        "predicateDrawUniformity.write(" in block and
        "native_sm3_ifc_is_quad_uniform(" in block and
        "predicateDrawUniformity.uniform_flow() &&" in block and
        "predicateDrawUniformity.begin_if(" in block and
        "predicateDrawUniformity.end_if()" in block and
        "derivativeUniformity.implicit_sampling_safe()" in block,
        "draw-uniform SETP source, condition and loop provenance")
require("instruction.opcode == D3DSIO_TEX &&" in block and
        "!predicateDrawUniformity.implicit_sampling_safe(true)" in block and
        "!predicateDrawUniformity.implicit_sampling_safe(sourcePredicated)" in block,
        "unproven p0 must still reject implicit native TEX")
require("native_sm3_texture_mode_allowed_in_control_flow(" in block and
        "!derivativeUniformity.implicit_sampling_safe()" in block and
        "native_sm3_scalar_predicate(" in block and
        "append_native_sm3_predicated_begin(" in block and
        "append_native_sm3_texture2d_sample(" in block,
        "branch divergence checks and real texture codegen remain connected")
require("GetPixelShaderConstantF(" in bridge and
        "context->PSSetShader(" in bridge and
        "context->DrawIndexed(" in bridge and "context->Draw(" in bridge,
        "real game pixel constants and GPU Draw/DrawIndexed linkage")
cc = shutil.which("g++") or shutil.which("clang++")
require(cc is not None, "C++17 compiler missing")
with tempfile.TemporaryDirectory() as directory:
    exe = str(Path(directory) / "sm3_predicated_tex")
    subprocess.run([cc, "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic",
                    str(root / "tools/dx11_sm3_uniform_predicate_texture_probe_01021.cpp"),
                    "-o", exe], check=True)
    subprocess.run([exe], check=True)
print("01021 uniform SETP predicated texture native Draw compiled PASS; Quest3 UNTESTED")
