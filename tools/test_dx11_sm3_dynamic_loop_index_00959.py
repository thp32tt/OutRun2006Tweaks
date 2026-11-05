#!/usr/bin/env python3
"""Covers live i#.xyz -> native SM3 dynamic c[base+aL] -> Draw fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_backend.cpp").read_text()
header = (root / "src/vr/d3d11/native_backend.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
flow = (root / "src/vr/d3d11/native_sm3_repeat_flow.hpp").read_text()
for item in (
    "indexedLoopLimits[range.integerRegister]",
    "constantLimit - reg", "if (range.dynamic)",
    "vertexIndexedLimits", "pixelIndexedLimits",
    "candidate.vertexLoopIndexedConstantEnd = vertexIndexedLimits",
    "candidate.pixelLoopIndexedConstantEnd = pixelIndexedLimits",
    'value = "r283_c[" + std::to_string(reg) + " + r283_aL]"',
    "if (defPresent[k]) return false",
):
    assert item in source, item
assert "loopRanges.empty() || loopRanges.back().dynamic" not in source
for item in ("vertexLoopIndexedConstantEnd", "pixelLoopIndexedConstantEnd"):
    assert item in header and item in bridge
assert bridge.count("native_sm3_live_loop_indexed_bounds_valid(") == 2
assert bridge.index("native_sm3_live_loop_indexed_bounds_valid(") < bridge.index(
    "ensure_full_game_upload_buffer(", bridge.index("native_sm3_live_loop_indexed_bounds_valid("))
assert "if (last < 0 || start >= static_cast<int>(end)" in flow
assert "last >= static_cast<int>(end)" in flow
print("Dynamic SM3 indexed c# source and game Draw admission linked; HMD UNTESTED")
