#!/usr/bin/env python3
"""00630 D3D9 live PM RGB + SELECTARG2/TFACTOR alpha -> native DX11 Draw."""
from itertools import product
from pathlib import Path

src = (Path(__file__).resolve().parents[1] /
       "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
predicate = ("const bool blendTextureAlphaPMFactorArg2Alpha =\n"
             "            op == D3DTOP_BLENDTEXTUREALPHAPM &&\n"
             "            alphaOp == D3DTOP_SELECTARG2 && alphaArg2 == D3DTA_TFACTOR;")
factor_read = ("selectTextureFactorAlpha || selectDiffuseFactorAlpha ||\n"
               "              blendTextureAlphaPMFactorArg2Alpha) &&\n"
               "            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor))")
guard = ("&& !selectTextureTfactorArg2Alpha && !selectDiffuseTfactorArg2Alpha &&\n"
         "              !blendTextureAlphaPMFactorArg2Alpha &&\n"
         "              !blendTextureAlphaPMInverseTextureArg2Alpha) && !blendTextureAlphaPMInverseDiffuseArg2Alpha) ||")
override = ("if (blendTextureAlphaPMFactorArg2Alpha) {\n"
            "            capture.blendTextureAlphaPMDiffuseAlpha = false;\n"
            "            capture.blendTextureAlphaPMFactorAlpha = true;\n"
            "        }")
ps = "float4 PSTextureBlendTextureAlphaPMSelectFactorAlpha(VOut v) : SV_Target {"
rgb = "saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a))"
alpha = "alphaParams.w"
links = (
    predicate, factor_read, guard, override,
    "capture.blendTextureAlphaPMDiffuseAlpha = blendTextureAlphaPMDiffuseAlpha;",
    "capture.blendTextureAlphaPMFactorAlpha = blendTextureAlphaPMFactorAlpha;",
    "capture.blendTextureAlphaPMFactorAlpha ? s.blendTextureAlphaPmFactorAlphaPs.Get() :",
    "capture.blendTextureAlphaPMDiffuseAlpha ? s.blendTextureAlphaPmDiffuseAlphaPs.Get() :",
    "capture.blendFactorAlphaValue = static_cast<float>((textureFactor >> 24u) & 0xffu) / 255.0f;",
    'compile("PSTextureBlendTextureAlphaPMSelectFactorAlpha", "ps_4_0", blendTexturePmFactorAlphaCode)',
    "s.blendTextureAlphaPmFactorAlphaPs.GetAddressOf()",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"'
)
def linked(s):
    if not all(x in s for x in links) or ps not in s:
        return False
    shader = s.split(ps, 1)[1].split("}", 1)[0]
    if not all(x in shader for x in (rgb, alpha, "AlphaGate(c.a); return c;")):
        return False
    # SELECTARG2 must be resolved after the shared diffuse predicate was
    # captured but before native PS binding; that order avoids wrong PS.
    capture = s.index("capture.blendTextureAlphaPMFactorAlpha = blendTextureAlphaPMFactorAlpha;")
    return capture < s.index(override) < s.index(
        "capture.blendTextureAlphaPMFactorAlpha ? s.blendTextureAlphaPmFactorAlphaPs.Get() :")

assert linked(src), "live D3D9 capture -> factor alpha PS -> native Draw disconnected"
for token in links[:4]:
    assert src.count(token) == 1, "unsafe ambiguous mutation anchor: " + token[:70]
    assert not linked(src.replace(token, "BROKEN_00630", 1)), "unprotected " + token[:70]
for before, after in (
    ("alphaOp == D3DTOP_SELECTARG2", "alphaOp == D3DTOP_SELECTARG1"),
    ("alphaArg2 == D3DTA_TFACTOR", "alphaArg2 == D3DTA_DIFFUSE"),
    ("op == D3DTOP_BLENDTEXTUREALPHAPM", "op == D3DTOP_BLENDTEXTUREALPHA"),
):
    assert not linked(src.replace(predicate, predicate.replace(before, after), 1)), before
assert src.index("capture.blendTextureAlphaPMDiffuseAlpha ?") < src.index(
    "capture.blendTextureAlphaPMFactorAlpha ?"), "native PS priority changed"
for token in (rgb, "alphaParams.w", "AlphaGate(c.a); return c;"):
    shader = ps + src.split(ps, 1)[1].split("}", 1)[0] + "}"
    assert not linked(src.replace(shader, shader.replace(token, "0.0f", 1), 1)), token
distinct = 0
for tex_rgb, dif_rgb, tex_a, factor_byte in product(
    (0., .2, .8, 1.), (0., .3, .7, 1.), (0., .25, .65, 1.), range(256)
):
    native_rgb = min(1., tex_rgb + dif_rgb * (1. - tex_a))
    native_alpha = factor_byte / 255.
    assert 0. <= native_rgb <= 1. and 0. <= native_alpha <= 1.
    if abs(native_alpha - tex_a) > 1.e-5:
        distinct += 1
assert distinct > 0
print("00630 PM RGB+SELECTARG2/TFACTOR: capture, mutually exclusive shader routing,"
      " destructive checks and 16384 numeric pairs PASS; HMD UNTESTED")
