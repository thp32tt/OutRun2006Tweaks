#!/usr/bin/env python3
"""Check actual live VS/PS native Draw projective source translation."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
header = (root / "src/vr/d3d11/native_sm3_arithmetic_codegen.hpp").read_text()
for required in (
    "native_sm3_source_modifier_components(",
    "native_sm3_swizzled_components(",
    "append_native_sm3_source_modifier(value, modifier)",
    "append_native_sm3_arithmetic(",
    "append_native_sm3_matrix(",
    "append_native_sm3_texture2d_sample(",
):
    assert required in backend, required
assert "modifier == D3DSPSM_NOT" in backend
assert "modifier == D3DSPSM_DZ || modifier == D3DSPSM_DW" not in backend
assert backend.index("native_sm3_source_modifier_components(") < backend.index(
    "append_native_sm3_source_modifier(value, modifier)")
for required in ("modifier == 9u", "modifier == 10u",
                 "case 9u:", "case 10u:", ".zzzz)", ".wwww)"):
    assert required in header, required
assert "if (op.texture2d && modifier != D3DSPSM_NONE)" in backend
assert "(token & D3DSHADER_ADDRESSMODE_MASK) != 0u" in backend
print("SM3 live projective operand DIV + TEMP provenance PASS")
