#!/usr/bin/env python3
"""Check actual live VS/PS native Draw projective source translation."""
from pathlib import Path
import re

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
# 00954 extends the actual texture coordinate and derivative shader path
# while retaining the non-vector sampler and reserved modifier fallback.
# A cube-sampler extension shares the actual fail-closed TEX* operand guard.
# Check the complete ternary so neither branch can bypass source validation.
def valid_texture_guard(text: str) -> bool:
    pattern = (r"if\s*\(op\.texture2d\s*&&\s*!\s*\(op\.textureCube\s*\?"
               r"\s*native_sm3_cube_modifier_supported\(op\.textureMode, i, modifier\)"
               r"\s*:\s*native_sm3_texture_modifier_supported\(op\.textureMode, i, modifier\)\)\)")
    return re.search(pattern, text) is not None

assert valid_texture_guard(backend), "TEX* cube/2D source modifier guard missing"
for original, mutation in (
    ("!(op.textureCube", "(op.textureCube"),
    ("native_sm3_cube_modifier_supported(op.textureMode, i, modifier)", "true"),
    ("native_sm3_texture_modifier_supported(op.textureMode, i, modifier)", "true"),
):
    assert original in backend, original
    assert not valid_texture_guard(backend.replace(original, mutation, 1)), original
assert "modifier != D3DSPSM_NONE || swizzle != 0xe4u" in backend
assert "(token & D3DSHADER_ADDRESSMODE_MASK) != 0u" in backend
print("SM3 live projective operand DIV + TEMP provenance PASS")
