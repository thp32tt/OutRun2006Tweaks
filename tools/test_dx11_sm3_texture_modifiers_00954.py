#!/usr/bin/env python3
"""Verify SM3 live TEXLD family source modifier and original renderer fallback."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
texture = (root / "src/vr/d3d11/native_sm3_texture_codegen.hpp").read_text()
arithmetic = (root / "src/vr/d3d11/native_sm3_arithmetic_codegen.hpp").read_text()
assert "native_sm3_texture_modifier_supported(" in texture
assert "return modifier == 0u;" in texture
assert "modifier <= 12u" in texture
assert "!native_sm3_texture_modifier_supported(" in backend
assert "if (op.texture2d && modifier != D3DSPSM_NONE)" not in backend
for condition in ("!samplerDeclared[reg]", "!sampler2dDeclared[reg]",
                  "modifier != D3DSPSM_NONE || swizzle != 0xe4u"):
    assert condition in backend, condition
for snippet in ("native_sm3_texture_source_components(op.textureMode, i)",
                "native_sm3_source_modifier_components(",
                "native_sm3_swizzled_components(",
                "(tempWritten[reg] & required) != required",
                "append_native_sm3_source_modifier(value, modifier)",
                "append_native_sm3_texture2d_sample("):
    assert snippet in backend, snippet
assert backend.index("native_sm3_texture_modifier_supported(") < backend.index(
    "append_native_sm3_source_modifier(value, modifier)")
assert backend.index("append_native_sm3_source_modifier(value, modifier)") < backend.index(
    "append_native_sm3_texture2d_sample(")
assert "case 9u:" in arithmetic and "case 10u:" in arithmetic
for code in ("Sample(", "SampleBias(", "SampleLevel(", "SampleGrad("):
    assert code in texture, code
print("SM3 live TEXLD source modifiers + register provenance + sampler fallback PASS")
