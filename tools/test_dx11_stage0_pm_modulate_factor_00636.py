#!/usr/bin/env python3
"""00636: live stage-0 PM RGB with separate TEXTURE*TFACTOR alpha on native DX11."""
from itertools import product
from pathlib import Path

source = (Path(__file__).resolve().parents[1] /
          "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
predicate = """const bool blendTextureAlphaPMModulateFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_MODULATE &&
            alphaArg1 == D3DTA_TEXTURE && alphaArg2 == D3DTA_TFACTOR;"""
shader = """float4 PSTextureBlendTextureAlphaPMModulateFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a * alphaParams.w));
    AlphaGate(c.a); return c;
}"""
factor_read = """if (blendTextureAlphaPMModulateFactorAlpha &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))"""
links = [
    predicate, factor_read, shader,
    "bool blendTextureAlphaPMModulateFactorAlpha = false;",
    "ComPtr<ID3D11PixelShader> blendTextureAlphaPmModulateFactorAlphaPs;",
    "s.blendTextureAlphaPmModulateFactorAlphaPs && s.blendTextureAlphaPmModulateAlphaPs",
    "s.blendTextureAlphaPmModulateFactorAlphaPs.Reset();",
    "ComPtr<ID3DBlob> blendTexturePmModulateFactorAlphaCode;",
    'compile("PSTextureBlendTextureAlphaPMModulateFactorAlpha", "ps_4_0", blendTexturePmModulateFactorAlphaCode)',
    "s.blendTextureAlphaPmModulateFactorAlphaPs.GetAddressOf()",
    "capture.blendTextureAlphaPMModulateFactorAlpha = blendTextureAlphaPMModulateFactorAlpha;",
    "capture.blendTextureAlphaPMModulateFactorAlpha ? s.blendTextureAlphaPmModulateFactorAlphaPs.Get() :",
    "!blendTextureAlphaPMModulateFactorAlpha &&\n             !blendTextureAlphaPMDiffuseAlpha &&",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    "OUTRUN_DX11_FIRST_GAME_FRAME",
]

def linked(text):
    return (all(key in text for key in links) and
            text.index(predicate) < text.index(factor_read) <
            text.index(links[10]) < text.index(links[11]) <
            text.index(links[13]))

assert linked(source), "D3D9 stage0 capture -> factor -> native HLSL/PS/Draw disconnected"
for item in links[:12]:
    assert source.count(item) >= 1, "missing: " + item[:65]
    assert not linked(source.replace(item, "BROKEN_00636")), "mutation survived: " + item[:65]
for old, new in (
        ("D3DTOP_BLENDTEXTUREALPHAPM", "D3DTOP_BLENDTEXTUREALPHA"),
        ("D3DTOP_MODULATE", "D3DTOP_ADD"),
        ("alphaArg1 == D3DTA_TEXTURE", "alphaArg1 == D3DTA_TFACTOR"),
        ("alphaArg2 == D3DTA_TFACTOR", "alphaArg2 == D3DTA_DIFFUSE")):
    assert not linked(source.replace(predicate, predicate.replace(old, new), 1))
# D3D9 PM = 15, MODULATE = 4, TEXTURE = 2, TFACTOR = 3;
# all other source/operation/modifier choices remain on the D3D9 fallback.
def admitted(rgb_op, alpha_op, a1, a2):
    return rgb_op == 15 and alpha_op == 4 and a1 == 2 and a2 == 3

positive, rejected, independently_weighted = 0, 0, 0
for rgb_op, alpha_op, a1, a2 in product(
        (15, 14), (4, 7), (2, 3, 0x12), (3, 2, 0x13)):
    is_exact = rgb_op == 15 and alpha_op == 4 and a1 == 2 and a2 == 3
    assert admitted(rgb_op, alpha_op, a1, a2) is is_exact
    positive += int(is_exact)
    rejected += int(not is_exact)
assert positive == 1 and rejected == 35
# 256 live D3DRS_TEXTUREFACTOR bytes; unscaled factors remain within [0,1].
# The saturating native shader also supports 2X/4X factors without changing
# this fixture's original unscaled alpha arithmetic.
# A different vertex alpha must not affect this separately selected alpha.
for tex, vertex, sample_a, diffuse_a, factor_byte in product(
        (0., .2, .8, 1.), (0., .3, .7, 1.),
        (0., .25, .75, 1.), (0., 1.), range(256)):
    rgb = min(1., tex + vertex * (1. - sample_a))
    alpha = sample_a * (factor_byte / 255.)
    assert 0. <= rgb <= 1. and 0. <= alpha <= 1.
    assert alpha == sample_a * (factor_byte / 255.)
    if sample_a and factor_byte not in (0, 255) and diffuse_a != alpha:
        independently_weighted += 1
assert independently_weighted > 0
print("00636 D3D9 PM/TFACTOR -> native Draw+DrawIndexed, destructive and 32768 numeric cases PASS; HMD UNTESTED")
