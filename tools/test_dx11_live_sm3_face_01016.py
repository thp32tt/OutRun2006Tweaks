#!/usr/bin/env python3
"""Real ps_3_0 FACE declaration/linkage/condition native HLSL Draw regression."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
pipeline = (root / "src/vr/d3d11/pipeline_translation.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
def require(ok, reason):
    if not ok:
        raise SystemExit("01016 FACE native game compare FAIL: " + reason)
shader = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
require("D3DSMO_FACE" in pipeline and
        "native_sm3_face_declaration(" in pipeline and
        "pixelFace ? D3DDECLUSAGE_PSIZE" in pipeline and
        "mix(pixelFace ? 0x56464143u : 0x56504f53u)" in pipeline and
        "if (!clipPosition) return out;" in pipeline,
        "authentic face DCL, separated shader pair hash and real VS clip source")
require("faceDeclared = true;" in shader and
        "if (faceDeclared) return false;" in shader and
        "native_sm3_face_scalar_source(requiredComponents)" in shader and
        "value = native_sm3_face_compare_hlsl();" in shader and
        'pixelFace ? "bool " : "float4 "' in shader and
        '"r283_frontface"' in shader and
        'label = pixelFace ? "SV_IsFrontFace" : "SV_Position"' in backend,
        "real ps raster bool feeds signed face scalar comparisons")
require("else if (kind == D3DSPR_MISCTYPE)" in shader and
        "native_sm3_face_scalar_source(required)" not in shader and
        "native_sm3_pixel_position_source(required)" in shader,
        "arithmetic/TEX vFace must fail closed; VPOS still separate")
require("context->PSSetShader(" in bridge and
        "context->DrawIndexed(" in bridge and "context->Draw(" in bridge,
        "native game shader still binds D3D11 Draw/DrawIndexed")
compiler = shutil.which("g++") or shutil.which("clang++")
require(bool(compiler), "C++17 compiler unavailable")
with tempfile.TemporaryDirectory() as directory:
    exe = Path(directory) / "sm3_face"
    subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
        "-Werror", "-pedantic", "-I", str(root / "src/vr/d3d11"),
        str(root / "tools/dx11_sm3_face_compare_01016.cpp"),
        "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("01016 FACE compare native linkage PASS; actual game/Quest3 UNTESTED")
