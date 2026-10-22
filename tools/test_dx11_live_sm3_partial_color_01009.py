#!/usr/bin/env python3
"""01009 native live D3D9 SM3 partial oC0 color GPU Draw and fallback."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root/"src/vr/d3d11/native_backend.cpp").read_text()
metadata = (root/"src/vr/d3d11/native_backend.hpp").read_text()
bridge = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
sm3 = bridge.split("bool submit_live_sm3_game_draw(",1)[1].split(
    "// Reuse geometric growth buffers",1)[0]
def require(value,message):
    if not value: raise SystemExit("01009 partial-color FAIL: "+message)
for word in ("unsigned* writtenColorMask = nullptr",
             "writtenColorMask = vertexStage ? 0u : outputWritten[0]",
             "&pixelWrittenColorMask)", "candidate.pixelWrittenColorMask =",
             "candidate.pixelDepthOnly = pixelWritesDepth && !pixelWritesColor;"):
    require(word in backend,"real shader HLSL/metadata: "+word)
require("std::uint8_t pixelWrittenColorMask{};" in metadata,"PS metadata")
for word in ("GetRenderState(D3DRS_COLORWRITEENABLE, &colorMask)",
             "native_sm3_partial_color_draw_allowed(",
             "pipeline.program.pixelWrittenColorMask",
             "context->OMSetBlendState(", "context->PSSetShader(",
             "context->DrawIndexed(", "context->Draw("):
    require(word in sm3,"live native GPU path: "+word)
require(sm3.index("native_sm3_partial_color_draw_allowed(") <
        sm3.index("context->OMSetBlendState(") <
        sm3.index("context->DrawIndexed("),"admission before GPU Draw")
compiler=shutil.which("g++") or shutil.which("clang++")
if compiler:
    with tempfile.TemporaryDirectory() as folder:
        exe=Path(folder)/"partial_color"
        subprocess.run([compiler,"-std=c++17","-Wall","-Wextra","-Werror",
                        "-pedantic","-I",str(root/"src/vr/d3d11"),
                        str(root/"tools/dx11_live_sm3_partial_color_01009.cpp"),
                        "-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
print("01009 partial SM3 game GPU color source integration PASS; HMD UNTESTED")
