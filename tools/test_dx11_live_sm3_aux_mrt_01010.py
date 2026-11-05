#!/usr/bin/env python3
"""01010: real game ps_3_0 ignored auxiliary MRT outputs with safe native fallback."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
compiler = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
draw = bridge.split("bool submit_live_sm3_game_draw(", 1)[1].split(
    "// Reuse geometric growth buffers", 1)[0]

def require(condition, message):
    if not condition:
        raise SystemExit("01010 auxiliary MRT GPU integration FAIL: " + message)

for token in ('#include "native_sm3_aux_color_output.hpp"',
              "std::array<bool, 4> ignoredMrtOutputUsed{};",
              "native_sm3_aux_color_destination(",
              "ignoredMrtOutputUsed[op.destinationRegister] = true;",
              "outputWritten[op.destinationRegister], mask, op.predicated);",
              "append_native_sm3_ignored_mrt_locals(translated, ignoredMrtOutputUsed);",
              '"r283_oC" + std::to_string(op.destinationRegister)'):
    require(token in compiler or token in backend, "pixel compile/codegen " + token)

require(compiler.index("append_native_sm3_ignored_mrt_locals(") <
        compiler.index("for (std::size_t i = 0u; i < operations.size(); ++i)"),
        "declare actual auxiliary shader locals before executing instructions")
require('dest = op.destinationRegister == 0u ? "r283_color"' in compiler,
        "primary oC0 must remain SV_Target0")
require('else if (outputWritten[0] == 0u' in compiler,
        "no missing primary color/depth admission")
require('GetRenderTarget(slot, extra.GetAddressOf())' in draw and
        'GetRenderState(extraColorMasks[slot - 1u]' in draw and
        'GameNativeInertStencilMrt::extra_target_inert(true, extraMask)' in draw,
        "writable MRT1..3 must remain D3D9-owned")
require(draw.index("GameNativeInertStencilMrt::extra_target_inert(true, extraMask)") <
        draw.index("context->DrawIndexed("),
        "MRT fail-closed must precede native GPU DrawIndexed/Draw")
require('context->OMSetRenderTargets(\n        1u, &rtv' in draw,
        "native main RTV must not write unknown secondary targets")
cxx = shutil.which("g++") or shutil.which("clang++")
if not cxx:
    raise SystemExit("01010 auxiliary MRT GPU integration FAIL: C++ compiler unavailable")
with tempfile.TemporaryDirectory() as folder:
    exe = Path(folder) / "aux_mrt"
    subprocess.run([cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                    "-pedantic", "-I", str(root / "src/vr/d3d11"),
                    str(root / "tools/dx11_live_sm3_aux_mrt_01010.cpp"),
                    "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("01010 genuine shader auxiliary MRT output + inert source RT guard PASS; HMD UNTESTED")
