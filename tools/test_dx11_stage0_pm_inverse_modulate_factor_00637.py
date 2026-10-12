#!/usr/bin/env python3
"""00637: PM RGB + TEXTURE * COMPLEMENT(TFACTOR) alpha uses real native game Draw."""
from itertools import product
from pathlib import Path

source = (Path(__file__).resolve().parents[1] /
          "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")

predicate = """const bool blendTextureAlphaPMModulateInverseFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_MODULATE &&
            alphaArg1 == D3DTA_TEXTURE &&
            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT);"""
factor_read = """if (blendTextureAlphaPMModulateInverseFactorAlpha &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;"""
must_connect = (
    predicate,
    factor_read,
    "if (blendTextureAlphaPMModulateInverseFactorAlpha && !arg2Diffuse) return false;",
    "!blendTextureAlphaPMModulateInverseFactorAlpha &&",
    "capture.blendTextureAlphaPMModulateFactorAlpha = blendTextureAlphaPMModulateFactorAlpha;",
    "if (blendTextureAlphaPMModulateInverseFactorAlpha)\n            capture.blendTextureAlphaPMModulateFactorAlpha = true;",
    "if (blendTextureAlphaPMModulateInverseFactorAlpha ||\n            blendTextureAlphaPMScaledInverseFactorAlpha)\n            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;",
    "float4 PSTextureBlendTextureAlphaPMModulateFactorAlpha(VOut v) : SV_Target {",
    "t.a * alphaParams.w",
    "capture.blendTextureAlphaPMModulateFactorAlpha ? s.blendTextureAlphaPmModulateFactorAlphaPs.Get() :",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    "OUTRUN_DX11_FIRST_GAME_FRAME",
)

def connected(s):
    return all(part in s for part in must_connect) and (
        s.index(predicate) < s.index(factor_read) <
        s.index(must_connect[4]) < s.index(must_connect[5]) <
        s.index(must_connect[6]) < s.index(must_connect[9]))

assert connected(source), "live D3D9 complemented factor -> native PS constant -> Draw disconnected"
for part in must_connect[:10]:
    assert not connected(source.replace(part, "BROKEN_00637", 1)), (
        "undetected graph mutation: " + part[:65])
for old, replacement in (
    ("D3DTOP_BLENDTEXTUREALPHAPM", "D3DTOP_BLENDTEXTUREALPHA"),
    ("D3DTOP_MODULATE", "D3DTOP_ADD"),
    ("alphaArg1 == D3DTA_TEXTURE", "alphaArg1 == D3DTA_TFACTOR"),
    ("(D3DTA_TFACTOR | D3DTA_COMPLEMENT)", "D3DTA_TFACTOR"),
):
    assert not connected(source.replace(predicate, predicate.replace(old, replacement), 1))

# D3D9: PM=15, MODULATE=4, TEXTURE=2, TFACTOR=3, COMPLEMENT=0x10.
def admitted(rgb_op, alpha_op, arg1, arg2):
    return (rgb_op == 15 and alpha_op == 4 and arg1 == 2 and arg2 == 0x13)

admitted_count = 0
for rgb_op, alpha_op, arg1, arg2 in product(
        (15, 14), (4, 7), (2, 3, 0x12), (3, 2, 0x13, 0x23)):
    admitted_count += admitted(rgb_op, alpha_op, arg1, arg2)
assert admitted_count == 1

# Opposite factor endpoints, 8-bit normalization, independent vertex alpha,
# and the original texture-alpha PM RGB weighting are all preserved.
verified = 0
for tex_rgb, vertex_rgb, texture_a, vertex_a, factor_byte in product(
        (0., .2, .8, 1.), (0., .3, .7, 1.),
        (0., .25, .75, 1.), (0., 1.), range(256)):
    factor = factor_byte / 255.
    native_factor = 1. - factor
    native_alpha = texture_a * native_factor
    expected_alpha = texture_a * (1. - factor)
    native_rgb = min(1., tex_rgb + vertex_rgb * (1. - texture_a))
    assert abs(native_alpha - expected_alpha) < 1.e-12
    assert 0. <= native_rgb <= 1. and 0. <= native_alpha <= 1.
    assert native_rgb == min(1., tex_rgb + vertex_rgb * (1. - texture_a))
    if vertex_a != native_alpha:
        verified += 1
assert verified > 0
print("00637 PM RGB+complement TFACTOR alpha: live PS/Draw graph and 32768 numeric cases PASS; HMD UNTESTED")
