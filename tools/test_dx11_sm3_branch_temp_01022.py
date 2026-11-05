#!/usr/bin/env python3
"""01022: native real-game branch TEMP to IFC texture Draw compiled regression."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
block = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
def require(ok, label):
    if not ok:
        raise SystemExit("01022 native branch TEMP regression FAIL: " + label)
require("tempDrawUniformity.begin_if(uniformComparison)" in block
        and "tempDrawUniformity.begin_if(true)" in block
        and "tempDrawUniformity.otherwise()" in block
        and "tempDrawUniformity.end_if()" in block
        and "tempDrawUniformity.begin_loop()" in block
        and "tempDrawUniformity.end_loop()" in block
        and "tempDrawUniformity.uniform_flow() && !op.predicated" in block,
        "source IF/IFC/ELSE/ENDIF/REP/LOOP provenance linkage")
require("native_sm3_ifc_is_quad_uniform(" in block
        and "tempDrawUniformity.contains(reg, requiredComponents)" in block,
        "live per-lane IF condition provenance")
require("!derivativeUniformity.implicit_sampling_safe()" in block
        and "native_sm3_texture_mode_allowed_in_control_flow(" in block
        and "append_native_sm3_texture2d_sample(" in block,
        "conditional SM3 native tex sampling guards")
require("GetPixelShaderConstantF(" in bridge and "context->DrawIndexed(" in bridge
        and "context->Draw(" in bridge, "native game shader Draw linkage")
cc = shutil.which("g++") or shutil.which("clang++")
require(cc is not None, "C++17 compiler missing")
with tempfile.TemporaryDirectory() as tmp:
    exe = str(Path(tmp) / "sm3_uniform_branch")
    subprocess.run([cc, "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic",
                    str(root / "tools/dx11_sm3_branch_temp_probe_01022.cpp"),
                    "-o", exe], check=True)
    subprocess.run([exe], check=True)
print("01022 C++17 native branch/IFC texture Draw source regression PASS; runtime UNTESTED")
