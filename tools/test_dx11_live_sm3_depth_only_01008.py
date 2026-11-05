#!/usr/bin/env python3
"""01008: depth-only live D3D9 SM3 -> native D3D11 shadow/occlusion Draw."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
metadata = (root / "src/vr/d3d11/native_backend.hpp").read_text()
start = bridge.index("bool submit_live_sm3_game_draw(")
end = bridge.index("// Reuse geometric growth buffers", start)
sm3 = bridge[start:end]
def require(test, message):
    if not test:
        raise SystemExit("01008 depth-only shader FAIL: " + message)
for fragment in ("!(depthWritten && outputWritten[0] == 0u)",
                 "depthWritten && outputWritten[0] == 0u",
                 "float main(R283Input input) : SV_Depth",
                 "return r283_depth.x;",
                 "candidate.pixelDepthOnly = pixelWritesDepth && !pixelWritesColor;"):
    require(fragment in backend, "shader conversion missing: " + fragment)
require("bool pixelDepthOnly{};" in metadata, "shader flag not retained")
for fragment in ("GetRenderState(D3DRS_COLORWRITEENABLE, &colorMask)",
                 "pipeline.program.pixelDepthOnly",
                 "native_sm3_depth_only_pass(",
                 "s.diagnosticDepthView.Get() != nullptr",
                 "context->OMSetBlendState(",
                 "context->DrawIndexed(", "context->Draw("):
    require(fragment in sm3, "real-game GPU render path missing: " + fragment)
require(sm3.index("pipeline.program.pixelDepthOnly") <
        sm3.index("context->DrawIndexed("), "depth-only validation must precede GPU Draw")
require("native_sm3_depth_target(" in sm3, "original depth admission lost")
compiler = shutil.which("g++") or shutil.which("clang++")
if compiler:
    with tempfile.TemporaryDirectory() as folder:
        executable = Path(folder) / "depth_only"
        subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-pedantic", "-I", str(root / "src/vr/d3d11"),
                        str(root / "tools/dx11_live_sm3_depth_only_01008.cpp"),
                        "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)
print("01008 native depth-only SM3 shader/GPU admission PASS; real game/HMD UNTESTED")
