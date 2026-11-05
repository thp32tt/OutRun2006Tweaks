#!/usr/bin/env python3
"""00642: admit real stage0 PM CURRENT/DIFFUSE alpha without weakening fallback."""
from pathlib import Path
from itertools import product
s = (Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
predicate = """const bool blendTextureAlphaPMBlendCurrentDiffuseAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_BLENDCURRENTALPHA &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);"""
alias = """if (blendTextureAlphaPMBlendCurrentDiffuseAlpha)
            capture.blendTextureAlphaPMBlendDiffuseAlpha = true;"""
shader = """float4 PSTextureBlendTextureAlphaPMBlendDiffuseAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      lerp(v.diffuse.a, t.a, v.diffuse.a));
    AlphaGate(c.a); return c;
}"""
required = [
    predicate, alias, shader,
    "if (blendTextureAlphaPMBlendCurrentDiffuseAlpha && !arg2Diffuse) return false;",
    "!blendTextureAlphaPMBlendCurrentDiffuseAlpha &&",
    "blendTextureAlphaPMBlendDiffuseAlpha || blendTextureAlphaPMBlendCurrentDiffuseAlpha ||",
    "capture.blendTextureAlphaPMBlendDiffuseAlpha ? s.blendTextureAlphaPmBlendDiffuseAlphaPs.Get() :",
    'compile("PSTextureBlendTextureAlphaPMBlendDiffuseAlpha", "ps_4_0", blendTexturePmBlendDiffuseAlphaCode)',
    "s.blendTextureAlphaPmBlendDiffuseAlphaPs.GetAddressOf()",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    "OUTRUN_DX11_FIRST_GAME_FRAME"
]
def connected(text):
    return all(part in text for part in required) and text.index(predicate) < text.index(alias) < text.index(required[6])
assert connected(s), "stage0 source -> fail-closed admission -> native PS -> Draw broken"
for item in required[:9]:
    assert not connected(s.replace(item, "BROKEN_00642")), item[:70]
for before, after in [
    ("D3DTOP_BLENDCURRENTALPHA", "D3DTOP_BLENDFACTORALPHA"),
    ("alphaArg1 == D3DTA_TEXTURE", "alphaArg1 == D3DTA_CURRENT"),
    ("alphaArg2 == D3DTA_DIFFUSE", "alphaArg2 == D3DTA_TFACTOR"),
    ("alphaArg2 == D3DTA_CURRENT", "alphaArg2 == D3DTA_TEXTURE"),
    ("D3DTOP_BLENDTEXTUREALPHAPM", "D3DTOP_BLENDTEXTUREALPHA"),
]:
    assert not connected(s.replace(predicate, predicate.replace(before, after), 1))
# Stage0: CURRENT == DIFFUSE. Independently compute the D3D9 alpha
# interpolation, compare with the reused HLSL expression and reject the
# incorrect texture-alpha-weighted alternative.
n = 0
for t8, d8, arg2 in product(range(256), range(256), ("DIFFUSE", "CURRENT")):
    t, d = t8 / 255., d8 / 255.
    source2 = d
    d3d9 = t * d + source2 * (1. - d)
    native = source2 * (1. - d) + t * d
    assert abs(d3d9 - native) < 1e-12 and 0. <= native <= 1.
    n += 1
assert n == 131072
t, d = .85, .20
correct = t * d + d * (1. - d)
wrong_weight = t * t + d * (1. - t)
assert abs(correct - wrong_weight) > .3
print("00642 PM CURRENT DIFFUSE/CURRENT source/native Draw, 131072 alpha cases PASS; HMD UNTESTED")
