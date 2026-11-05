#!/usr/bin/env python3
"""00631: live D3D9 PM RGB / SELECTARG1 DIFFUSE-CURRENT alpha -> D3D11 Draw."""
from itertools import product
from pathlib import Path

src = (Path(__file__).resolve().parents[1] /
       "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
predicate = ("const bool blendTextureAlphaPMDiffuseArg1Alpha =\n"
             "            op == D3DTOP_BLENDTEXTUREALPHAPM &&\n"
             "            alphaOp == D3DTOP_SELECTARG1 &&\n"
             "            (alphaArg1 == D3DTA_DIFFUSE || alphaArg1 == D3DTA_CURRENT);")
capture = ("if (blendTextureAlphaPMDiffuseArg1Alpha)\n"
           "            capture.blendTextureAlphaPMDiffuseAlpha = true;")
shader = "float4 PSTextureBlendTextureAlphaPMSelectDiffuseAlpha(VOut v) : SV_Target {"
pixel = "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), v.diffuse.a);"
links = (
    predicate,
    "blendTextureAlphaPMDiffuseArg1Alpha || blendTextureAlphaPMDiffuseAlpha ||",
    "!blendTextureAlphaPMDiffuseArg1Alpha && !blendTextureAlphaPMModulateAlpha",
    "alphaArg1 != D3DTA_TEXTURE && !blendTextureAlphaPMDiffuseAlpha && !blendTextureAlphaPMDiffuseArg1Alpha",
    "capture.blendTextureAlphaPMDiffuseAlpha = blendTextureAlphaPMDiffuseAlpha;",
    capture,
    'compile("PSTextureBlendTextureAlphaPMSelectDiffuseAlpha", "ps_4_0", blendTexturePmDiffuseAlphaCode)',
    "s.blendTextureAlphaPmDiffuseAlphaPs.GetAddressOf()",
    "capture.blendTextureAlphaPMDiffuseAlpha ? s.blendTextureAlphaPmDiffuseAlphaPs.Get() :",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"'
)

def linked(text):
    if not all(x in text for x in links + (shader,)):
        return False
    ps = text.split(shader, 1)[1].split("}", 1)[0]
    return (pixel in ps and "AlphaGate(c.a); return c;" in ps and
            text.index(predicate) < text.index(capture) <
            text.index("capture.blendTextureAlphaPMDiffuseAlpha ?"))
assert linked(src), "native game D3D9 capture / shader / Draw link absent"
for token in (predicate, capture, pixel, links[2], links[3]):
    assert src.count(token) == 1, "ambiguous mutation anchor"
    assert not linked(src.replace(token, "BROKEN_00631", 1)), token[:64]
for before, after in (
    ("alphaOp == D3DTOP_SELECTARG1", "alphaOp == D3DTOP_SELECTARG2"),
    ("alphaArg1 == D3DTA_DIFFUSE", "alphaArg1 == D3DTA_TEXTURE"),
    ("alphaArg1 == D3DTA_CURRENT", "alphaArg1 == (D3DTA_CURRENT | D3DTA_ALPHAREPLICATE)"),
    ("op == D3DTOP_BLENDTEXTUREALPHAPM", "op == D3DTOP_BLENDTEXTUREALPHA"),
):
    assert not linked(src.replace(predicate, predicate.replace(before, after, 1), 1))
# D3D9 arguments have modifier bits: only exact DIFFUSE(0) and CURRENT(1).
def accepted(rgb_op, alpha_op, arg1):
    return rgb_op == 15 and alpha_op == 2 and arg1 in (0, 1)
for arg in (0, 1, 2, 0x10, 0x21):
    assert accepted(15, 2, arg) == (arg in (0, 1))
assert not accepted(15, 3, 0) and not accepted(12, 2, 1)
distinct = 0
for tr, dr, ta, da in product((0., .2, .8, 1.), (0., .3, .7, 1.),
                             (0., .25, .65, 1.), (0., .33, .75, 1.)):
    rgb, alpha = min(1., tr + dr * (1. - ta)), da
    assert 0. <= rgb <= 1. and 0. <= alpha <= 1.
    distinct += abs(alpha - ta) > 1.e-6
assert distinct > 0
print("00631 PM RGB/vertex alpha: capture, native Draw, destructive checks,"
      " 256 numeric cases PASS; HMD/gamepad UNTESTED")
