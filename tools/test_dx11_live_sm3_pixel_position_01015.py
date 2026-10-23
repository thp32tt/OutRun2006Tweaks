#!/usr/bin/env python3
"""SM3 real game ps_3_0 DCL vPos -> linkage -> HLSL SV_Position."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
linkage = (root / "src/vr/d3d11/pipeline_translation.cpp").read_text()
header = (root / "src/vr/d3d11/native_sm3_interface_channels.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
def require(ok, reason):
    if not ok:
        raise SystemExit("01015 vPos integration FAIL: " + reason)

require("registerType == D3DSPR_MISCTYPE" in linkage and
        "D3DSMO_POSITION" in linkage and
        "pixelPosition ? 0u" in linkage and
        "native_sm3_pixel_position_declaration(" in linkage and
        "if (pixelInput.registerType == D3DSPR_MISCTYPE)" in linkage and
        "if (!clipPosition) return out;" in linkage,
        "real ps_3_0 DCL and VS->PS rasterizer provenance")
shader = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
require("positionDeclared = true;" in shader and
        shader.count("value = native_sm3_pixel_position_hlsl();") == 2 and
        "positionDeclaredMask = mask & 0x03u;" in shader and
        "(required & ~positionDeclaredMask)" in shader and
        "native_sm3_pixel_position_source(required)" in shader and
        "native_sm3_pixel_position_source(requiredComponents)" in shader and
        "std::string(\"r283_vpos\")" in shader and
        "label = \"SV_Position\";" in backend,
        "unique pixel system input and masked register reads in compiled HLSL")
require("physicalReadMask & ~0x03u" in header and
        "float4(0.5f, 0.5f, 0.0f, 0.0f)" in header and
        "vertexStage" in header and "registerIndex == 0u" in header,
        "reject vFace, vertex MISCTYPE, z/w and unsupported modifiers")
require("context->PSSetShader(" in bridge and
        "context->DrawIndexed(" in bridge and "context->Draw(" in bridge,
        "genuine native D3D11 game Draw/DrawIndexed remains linked")
compiler = shutil.which("g++") or shutil.which("clang++")
require(bool(compiler), "C++17 compiler missing")
with tempfile.TemporaryDirectory() as directory:
    exe = Path(directory) / "dx11_vpos"
    subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
        "-Werror", "-pedantic", "-I", str(root / "src/vr/d3d11"),
        str(root / "tools/dx11_sm3_pixel_position_01015.cpp"),
        "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("01015 D3D9 vPos native system semantic regression PASS; game/HMD UNTESTED")
