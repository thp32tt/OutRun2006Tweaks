#!/usr/bin/env python3
"""01023: compiled real-game SM3 IF/IFC SETP branch merge to native implicit TEX."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
predicate = (root / "src/vr/d3d11/native_sm3_predicate_flow.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
shader = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]

def require(condition, label):
    if not condition:
        raise SystemExit("01023 SM3 native predicate branch regression FAIL: " + label)

require("predicateDrawUniformity.begin_if(uniformComparison)" in shader and
        "predicateDrawUniformity.begin_if(true)" in shader and
        "predicateDrawUniformity.otherwise()" in shader and
        "predicateDrawUniformity.end_if()" in shader and
        shader.count("predicateDrawUniformity.begin_loop()") == 2 and
        shader.count("predicateDrawUniformity.end_loop()") == 2 and
        "predicateDrawUniformity.uniform_flow() &&" in shader,
        "real IFC/IF/ELSE/ENDIF/LOOP/REP SETP p0 branch provenance")
require("predicateDrawUniformity.implicit_sampling_safe(sourcePredicated)" in shader
        and "native_sm3_texture_mode_allowed_in_control_flow(" in shader
        and "append_native_sm3_texture2d_sample(" in shader
        and "append_native_sm3_predicated_begin(" in shader,
        "native implicit TEX/TEXLDP/TEXLDB and predicated sample code")
require("frame.entryUniform && !frame.wrotePredicate" in predicate and
        "thenUniform && otherwiseUniform" in predicate and
        "frame.entryUniform && !frame.wrotePredicate" in predicate,
        "varying branch and loop fail closed, uniform branch both arms merge")
require("GetPixelShaderConstantF(" in bridge and
        "context->PSSetShader(" in bridge and
        "context->Draw(" in bridge and "context->DrawIndexed(" in bridge,
        "live D3D9 shader ownership to D3D11 Draw and DrawIndexed")
compiler = shutil.which("g++") or shutil.which("clang++")
require(compiler is not None, "C++17 compiler absent")
with tempfile.TemporaryDirectory() as directory:
    executable = str(Path(directory) / "sm3_branch_predicate_draw")
    subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic",
                    str(root / "tools/dx11_sm3_branch_predicate_probe_01023.cpp"),
                    "-o", executable], check=True)
    subprocess.run([executable], check=True)
print("01023 native shader IF/IFC SETP/TEX branch compiled PASS; game/HMD UNTESTED")
