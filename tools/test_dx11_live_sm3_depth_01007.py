#!/usr/bin/env python3
"""01007: live programmable SM3 oDepth GPU SV_Depth and game fallback regression."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
backend_h = (root / "src/vr/d3d11/native_backend.hpp").read_text()
sm3 = bridge.split("bool submit_live_sm3_game_draw(", 1)[1].split(
    "// Reuse geometric growth buffers", 1)[0]
def require(ok, why):
    if not ok:
        raise SystemExit("01007 SM3 depth FAIL: " + why)
for t in ("D3DSPR_DEPTHOUT", "depthWritten = true",
          "native_sm3_depth_destination(", "float depth : SV_Depth;",
          "r283_out.depth = r283_depth.x;", "candidate.pixelWritesDepth = pixelWritesDepth",
          "if (op.flowKind != 0u) return false;"):
    require(t in backend, "SM3 PS oDepth translator not wired: " + t)
require("else if (op.destinationType == D3DSPR_COLOROUT)" in backend,
        "oDepth must not count toward COLOROUT completeness")
require("pixelWritesDepth && (alphaCompare != 0u || tableZFog)" in backend,
        "alpha/fog mixed depth shader must fail closed")
for t in ("game_native_depth_admission(", "pipeline.program.pixelWritesDepth",
          "s.diagnosticDepthView.Get() != nullptr",
          "native_sm3_depth_target(", "context->PSSetShader(",
          "context->DrawIndexed(", "context->Draw("):
    require(t in sm3, "game-owned Z through GPU Draw missing: " + t)
require(sm3.index("game_native_depth_admission(") <
        sm3.index("compile_native_live_sm3_program(") <
        sm3.index("s.diagnosticDepthView.Get() != nullptr") <
        sm3.index("context->DrawIndexed("), "draw depth owner ordering")
require("bool pixelWritesDepth{};" in backend_h, "native program metadata")
compiler = shutil.which("g++") or shutil.which("clang++")
if compiler:
    with tempfile.TemporaryDirectory() as temp:
        binary = Path(temp) / "sm3_depth"
        subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra",
                        "-Werror", "-pedantic", "-I", str(root / "src/vr/d3d11"),
                        str(root / "tools/dx11_live_sm3_depth_01007.cpp"),
                        "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
print("SM3 live native depth linkage and fail-closed source PASS (HMD UNTESTED)")
