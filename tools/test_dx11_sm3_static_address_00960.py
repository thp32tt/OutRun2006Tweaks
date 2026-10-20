#!/usr/bin/env python3
"""Exact game SM3 DEF -> MOVA a0.x -> c[base+a0] native VS/PS integration."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_backend.cpp").read_text()
helper = (root / "src/vr/d3d11/native_sm3_address_codegen.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
assert "D3DSIO_MOVA" in source and "D3DSPR_ADDR" in source
assert "defBits[srcReg][srcSwizzle & 3u]" in source
assert "native_sm3_static_mova_address(" in source
assert "native_sm3_static_address_const_index(" in source
assert "staticAddressIndex < 0" in source
assert "defPresent[index]" in source and "liveConstantsUsed = true" in source
assert "native_sm3_const_reference(" in source
assert "native_sm3_live_loop_indexed_bounds_valid(" in bridge
assert "stageLimit - base" in helper
assert "std::isfinite(value)" in helper
assert "NativeDrawPathActive" in bridge
print("SM3 constant DEF MOVA a0 indexed game shader integration: source guards present; gameplay UNTESTED")
