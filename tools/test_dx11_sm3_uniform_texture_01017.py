#!/usr/bin/env python3
"""Confirm compiled derivative flow is wired to genuine game shader/Draw."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
block = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
def need(ok, message):
    if not ok: raise SystemExit("01017 SM3 uniform texture FAIL: " + message)
need('native_sm3_derivative_uniformity.hpp' in backend and
     'NativeSm3DerivativeUniformity derivativeUniformity;' in block,
     "real native compiler owns the derivative state")
need('!derivativeUniformity.begin(native_sm3_ifc_is_quad_uniform(' in block and
     'scalarOrigins[0], scalarOrigins[1]' in block and
     'NativeSm3IfcScalarOrigin::PixelDependent' in block and
     'scalarOrigins[i] = NativeSm3IfcScalarOrigin::DrawFloatConstant;' in block and
     '!derivativeUniformity.begin(true)' in block and
     '!derivativeUniformity.end()' in block and
     '!derivativeUniformity.empty()' in block,
     "IFC/IF/ENDIF and final balanced-branch checks")
need('sourcePredicated || !derivativeUniformity.implicit_sampling_safe()' in block and
     'native_sm3_texture_mode_allowed_in_control_flow(' in block and
     'append_native_sm3_texture2d_sample(' in block,
     "real HLSL texture codegen enforces quad uniformity")
need('GetPixelShaderConstantB(' in bridge and
     'context->PSSetShader(' in bridge and
     'context->DrawIndexed(' in bridge and 'context->Draw(' in bridge,
     "live game bool constant and actual native GPU game Draw/DrawIndexed")
cc = shutil.which("g++") or shutil.which("clang++")
need(cc is not None, "C++ compiler missing")
with tempfile.TemporaryDirectory() as folder:
    exe = str(Path(folder) / "uniform_texture")
    subprocess.run([cc, "-std=c++17", "-O2", "-Wall", "-Wextra",
        "-Werror", "-pedantic", str(root / "tools/dx11_sm3_uniform_texture_01017.cpp"),
        "-o", exe], check=True)
    subprocess.run([exe], check=True)
print("01017 real SM3 IF b# / GPU TEXLD compile-path PASS; game/Quest3 UNTESTED")
