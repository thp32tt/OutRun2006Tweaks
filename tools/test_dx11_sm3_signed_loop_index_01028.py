#!/usr/bin/env python3
"""Signed SM3 LOOP c[base+aL] native VS/PS draw admission and fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
header = (root / "src/vr/d3d11/native_backend.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
flow = (root / "src/vr/d3d11/native_sm3_repeat_flow.hpp").read_text()
matrix = (root / "src/vr/d3d11/native_sm3_constant_codegen.hpp").read_text()
for token in ("indexedLoopLowerBounds.fill(-255)", "dynamicRelativeLowerBounds",
              "&vertexIndexedLower", "&pixelIndexedLower",
              "candidate.vertexLoopIndexedConstantLower = vertexIndexedLower",
              "candidate.pixelLoopIndexedConstantLower = pixelIndexedLower",
              "for (unsigned k = 0u; k < constantLimit; ++k)"):
    assert token in backend, token
for token in ("vertexLoopIndexedConstantLower", "pixelLoopIndexedConstantLower"):
    assert token in header and token in bridge, token
assert bridge.count("native_sm3_live_loop_indexed_bounds_valid(") == 2
assert bridge.index("native_sm3_live_loop_indexed_bounds_valid(") < bridge.index(
    "ensure_full_game_upload_buffer(", bridge.index("native_sm3_live_loop_indexed_bounds_valid("))
assert "minimum < lower || maximum >= end" in flow
assert "loopInclusiveLowerOffsets" in matrix and "required > low" in matrix
print("signed LOOP native C++ VS/PS Draw path linked; HMD UNTESTED")
