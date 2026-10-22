#!/usr/bin/env python3
"""Live SM3 programmable user clip planes: GPU VS clip distance, owner/fallback regression."""
from pathlib import Path
import subprocess
import shutil
import tempfile
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
header = (root / "src/vr/d3d11/live_game_sm3_user_clip.hpp").read_text()
sm3 = bridge.partition("bool submit_live_sm3_game_draw(")[2].partition(
    "// Reuse geometric growth buffers")[0]
def require(condition, reason):
    if not condition:
        raise SystemExit("DX11 real SM3 user clip FAIL: " + reason)
for token in ("D3DRS_CLIPPLANEENABLE", "D3DRS_CLIPPING", "GetClipPlane(",
              "MaxUserClipPlanes", "native_sm3_user_clip_admission(",
              "clip.active", "pipeline.userClipConstants",
              "context->VSSetConstantBuffers(4u, 1u, &clipBuffer)",
              "context->DrawIndexed(", "context->Draw("):
    require(token in sm3, "game-owned plane to native Draw disconnected: " + token)
require(sm3.index("native_sm3_user_clip_admission(") <
        sm3.index("compile_native_live_sm3_program(") <
        sm3.index("context->VSSetConstantBuffers(4u, 1u, &clipBuffer)") <
        sm3.index("context->DrawIndexed("), "source admission -> GPU compile/bind/draw order")
require("append_native_sm3_user_clip(vertexHlsl, userClip)" in backend,
        "native VS HLSL translator clip interface disconnected")
for token in ("SV_ClipDistance0", "SV_ClipDistance1", "dot(output.",
              "r283_clipOnA", "r283_clipPlanes[6]", "register(b4)"):
    require(token in header, "real shader clip distance missing: " + token)
compiler = shutil.which("g++") or shutil.which("clang++")
if compiler:
    with tempfile.TemporaryDirectory() as tmp:
        binary = Path(tmp) / "clip"
        subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-pedantic", "-I", str(root / "src/vr/d3d11"),
                        str(root / "tools/dx11_live_sm3_user_clip_01006.cpp"),
                        "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
print("DX11 SM3 live game user clip VS + original D3D9 fallback source PASS (HMD UNTESTED)")
