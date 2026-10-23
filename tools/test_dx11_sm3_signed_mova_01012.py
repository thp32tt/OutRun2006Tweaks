#!/usr/bin/env python3
"""Real VS3 DEF->MOVA rounding/signed relative scalar+matrix GPU materializer."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
address = (root / "src/vr/d3d11/native_sm3_address_codegen.hpp").read_text()
matrix = (root / "src/vr/d3d11/native_sm3_constant_codegen.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
def require(ok, message):
    if not ok:
        raise SystemExit("01012 native game MOVA FAIL: " + message)
require("staticAddressReady = true" in backend and
        "reg, staticAddressIndex," in backend and
        "int address = 0;" in backend,
        "authentic game shader MOVA offset routed to constant and matrix source")
require("_HLSL_MATERIALIZER_V15" in backend and
        "_TEX2D_IFC_PROVENANCE_V15" in backend,
        "invalidate old shader artifact identity")
require("fraction == 0.5f" in address and
        "static_cast<long long>(base) + address" in address,
        "signed D3D9 nearest conversion and fail-closed constant bank")
require("base + row, staticAddress," in matrix and
        "const auto first = static_cast<long long>(base) + staticAddress" in matrix,
        "source matrix rows inherit signed MOVA offset")
require("context->DrawIndexed(" in bridge and "context->Draw(" in bridge,
        "live GPU gameplay draws remain attached")
compiler = shutil.which("g++") or shutil.which("clang++")
require(compiler is not None, "C++ regression compiler unavailable")
with tempfile.TemporaryDirectory() as temp:
    binary = Path(temp) / "signed_mova"
    subprocess.run([
        compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-pedantic", "-Isrc/vr/d3d11",
        "tools/dx11_sm3_signed_mova_01012.cpp", "-o", str(binary)
    ], cwd=root, check=True)
    subprocess.run([str(binary)], cwd=root, check=True)
print("01012 signed/fractional MOVA native game constants regression PASS; real game/HMD UNTESTED")
