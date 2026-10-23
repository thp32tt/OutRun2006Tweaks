#!/usr/bin/env python3
"""Live shader-owned M*x* relative matrix -> native VS/PS draw integration."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
cpp = (root / "src/vr/d3d11/native_backend.cpp").read_text()
h = (root / "src/vr/d3d11/native_sm3_constant_codegen.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
assert "native_sm3_relative_matrix_references(" in cpp
assert "op.matrixRows, liveMatrix" in cpp
assert "liveConstantsUsed = true" in cpp
assert "indexedLoopLimits" in cpp and "dynamicRelativeLimits" in cpp
assert "r283_c[" in h and " + r283_aL]" in h
assert "dynamicExclusive = limit - base - rows + 1u" in h
assert "for (unsigned reg = base; reg < limit; ++reg)" in h
# Static MOVA matrices check the signed effective row span before indexing;
# the scalar index helper intentionally rejects encoded out-of-bank bases.
assert "const auto first = static_cast<long long>(base) + staticAddress" in h
assert "const auto last = first + static_cast<long long>(rows) - 1" in h
assert "if (first < 0 || last >= static_cast<long long>(limit))" in h
assert "const unsigned index = staticFirstIndex + row;" in h
assert "native_sm3_const_reference(" in h
assert "native_sm3_live_loop_indexed_bounds_valid(" in bridge
assert "if (relative && op.texture2d && i == 1u)" in cpp
print("SM3 relative matrix Draw pipeline wired with bounded aL/a0; runtime UNTESTED")
