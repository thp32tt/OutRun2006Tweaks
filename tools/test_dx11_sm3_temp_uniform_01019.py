#!/usr/bin/env python3
"""Compiled source-linked regression for game c# -> TEMP -> IFC native Draw."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
native = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/native_sm3_temp_draw_uniformity.hpp").read_text()
block = native.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]

def need(test, msg):
    if not test:
        raise SystemExit("01019 constant-derived TEMP native draw FAIL: " + msg)

need('#include "native_sm3_temp_draw_uniformity.hpp"' in native and
     "NativeSm3TempDrawUniformity tempDrawUniformity;" in block,
     "C++ HLSL parser must own per-Draw TEMP provenance")
need("tempDrawUniformity.contains(reg, requiredComponents)" in block and
     "scalarOrigins[i] =" in block and
     "NativeSm3IfcScalarOrigin::DrawFloatConstant" in block,
     "IFC scalar TEMP origin must reach derivative classifier")
need("native_sm3_source_modifier_components(" in block and
     "uniformPhysicalComponents" in block and
     "tempDrawUniformity.contains(" in block and
     "kind == D3DSPR_CONST && !relative" in block,
     "actual per-lane uniform arithmetic source propagation must be connected")
need("structuredFlow.empty() && !op.predicated" in block and
     "tempDrawUniformity.invalidate(scratch)" in block and
     "op.opcode != NativeSm3ArithmeticOpcode::DerivativeX" in block and
     "op.opcode != NativeSm3ArithmeticOpcode::DerivativeY" in block,
     "divergent/predicated/derivative/scratch writes must fail closed")
need("writtenMask &= 0x0fu" in header and
     "(masks_[reg] & requiredMask) == requiredMask" in header,
     "component-accurate write and scalar-read physical lane checks")
need("bool sourcesDrawUniform = sourceCount != 0u" in block and
     "sourcesDrawUniform = false;" in block and
     "kind == D3DSPR_TEMP &&" in block and
     "reg, uniformPhysicalComponents" in block and
     "op.matrixRowCount == 0u" in block and
     "sourcesDrawUniform;" in block,
     "pure arithmetic must propagate only proven, physical constant/TEMP lanes")
need("!op.texture2d && !op.texkill && !op.signScratch" in block and
     "tempDrawUniformity.write(" in block and
     "structuredFlow.empty() && !op.predicated" in block,
     "texture/scratch/predicate/branch destinations must never inherit uniformity")
need("context->PSSetShader(" in bridge and
     "context->DrawIndexed(" in bridge and "context->Draw(" in bridge,
     "live shader/DrawIndexed/Draw linkage is required")
cc = shutil.which("g++") or shutil.which("clang++")
need(cc is not None, "C++17 compiler unavailable")
with tempfile.TemporaryDirectory() as folder:
    exe = str(Path(folder) / "temp_uniform")
    subprocess.run([cc, "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic",
                    str(root / "tools/dx11_sm3_temp_uniform_probe_01019.cpp"),
                    "-o", exe], check=True)
    subprocess.run([exe], check=True)
print("01019 native Draw constant-derived TEMP IFC compiled regression PASS; HMD UNTESTED")
