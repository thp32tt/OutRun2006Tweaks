#!/usr/bin/env python3
"""Source-linked compiled regression for live D3D9 SM3 IFC(c#,c#) native Draw."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
flow = (root / "src/vr/d3d11/native_sm3_derivative_uniformity.hpp").read_text()
block = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
def need(ok, msg):
    if not ok: raise SystemExit("01018 real IFC(c#,c#) native Draw FAIL: " + msg)
need("NativeSm3IfcScalarOrigin::PixelDependent" in block and
     "scalarOrigins[i] = NativeSm3IfcScalarOrigin::DrawFloatConstant;" in block and
     "if (kind == D3DSPR_TEMP)" in block and
     "kind == D3DSPR_INPUT" in block and "kind == D3DSPR_MISCTYPE" in block,
     "original input/temp/system-dependent operands remain varying")
need("(token & D3DSHADER_ADDRESSMODE_MASK) != 0u" in block and
     "native_sm3_ifc_is_quad_uniform(\n                        scalarOrigins[0], scalarOrigins[1])" in block and
     "!derivativeUniformity.end()" in block,
     "nonrelative float source and balanced native IFC flow")
need("first == NativeSm3IfcScalarOrigin::DrawFloatConstant" in flow and
     "second == NativeSm3IfcScalarOrigin::DrawFloatConstant" in flow,
     "both operands required for actual draw-uniform branch")
need("native_sm3_texture_mode_allowed_in_control_flow(" in block and
     "sourcePredicated || !derivativeUniformity.implicit_sampling_safe()" in block and
     "append_native_sm3_texture2d_sample(" in block,
     "the native real shader TEXLD admission consumes IFC uniformity")
need("GetPixelShaderConstantF(" in bridge and
     "context->PSSetShader(" in bridge and
     "context->DrawIndexed(" in bridge and "context->Draw(" in bridge,
     "real game float constant capture and native Draw/DrawIndexed linkage")
cc = shutil.which("g++") or shutil.which("clang++")
need(cc is not None, "C++ compiler missing")
with tempfile.TemporaryDirectory() as folder:
    exe = str(Path(folder) / "uniform_ifc")
    subprocess.run([cc, "-std=c++17", "-O2", "-Wall", "-Wextra",
        "-Werror", "-pedantic", str(root / "tools/dx11_sm3_uniform_ifc_01018.cpp"),
        "-o", exe], check=True)
    subprocess.run([exe], check=True)
print("01018 compiled game IFC(c#,c#) native derivative-source path PASS; Quest3 UNTESTED")
