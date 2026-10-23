#!/usr/bin/env python3
"""00639: game-authored PM RGB with independent signed / signed2x TFACTOR alpha."""
from itertools import product
from pathlib import Path

src = (Path(__file__).resolve().parents[1] /
       "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
pred = """const bool blendTextureAlphaPMSignedFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            (alphaOp == D3DTOP_ADDSIGNED || alphaOp == D3DTOP_ADDSIGNED2X) &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_TFACTOR ||
             alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT));"""
shader = """float4 PSTextureBlendTextureAlphaPMSignedFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a + alphaParams.w - 0.5f));
    AlphaGate(c.a); return c;
}"""
shader2 = """float4 PSTextureBlendTextureAlphaPMSigned2XFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(2.0f * (t.a + alphaParams.w - 0.5f)));
    AlphaGate(c.a); return c;
}"""
graph = (
    pred, shader, shader2,
    "if (blendTextureAlphaPMSignedFactorAlpha &&\n            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))",
    "if (blendTextureAlphaPMSignedFactorAlpha && !arg2Diffuse) return false;",
    "!blendTextureAlphaPMSignedFactorAlpha &&",
    "capture.blendTextureAlphaPMSignedFactorAlpha = blendTextureAlphaPMSignedFactorAlpha;",
    "capture.blendTextureAlphaPMSigned2XFactorAlpha =\n            blendTextureAlphaPMSignedFactorAlpha && alphaOp == D3DTOP_ADDSIGNED2X;",
    "if (blendTextureAlphaPMSignedFactorAlpha &&\n            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT))\n            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;",
    'compile("PSTextureBlendTextureAlphaPMSignedFactorAlpha", "ps_4_0", blendTexturePmSignedFactorCode)',
    'compile("PSTextureBlendTextureAlphaPMSigned2XFactorAlpha", "ps_4_0", blendTexturePmSigned2XFactorCode)',
    "s.blendTextureAlphaPmSignedFactorAlphaPs.GetAddressOf()",
    "s.blendTextureAlphaPmSigned2XFactorAlphaPs.GetAddressOf()",
    "capture.blendTextureAlphaPMSigned2XFactorAlpha ? s.blendTextureAlphaPmSigned2XFactorAlphaPs.Get() :",
    "capture.blendTextureAlphaPMSignedFactorAlpha ? s.blendTextureAlphaPmSignedFactorAlphaPs.Get() :",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME", value, 8) == 1'
)

def connected(text):
    if not all(piece in text for piece in graph):
        return False
    return (text.index(pred) < text.index(graph[3]) < text.index(graph[4]) <
            text.index(graph[6]) < text.index(graph[7]) <
            text.index(graph[13]) < text.index(graph[15]))

assert connected(src), "stage0 capture -> signed factor -> native Draw disconnected"
for part in graph:
    assert not connected(src.replace(part, "REMOVED_00639", 1)), part[:88]
for before, after in (
    ("D3DTOP_BLENDTEXTUREALPHAPM", "D3DTOP_BLENDTEXTUREALPHA"),
    ("alphaArg1 == D3DTA_TEXTURE", "alphaArg1 == D3DTA_TFACTOR"),
    ("alphaArg2 == D3DTA_TFACTOR", "alphaArg2 == D3DTA_TEXTURE"),
    ("D3DTOP_ADDSIGNED2X", "D3DTOP_MODULATE4X"),
):
    assert not connected(src.replace(pred, pred.replace(before, after), 1))

# D3D9 stage0 op values: BLENDTEXTUREALPHAPM=15, ADDSIGNED=7,
# ADDSIGNED2X=8; TEXTURE=2, TFACTOR=3, COMPLEMENT=0x10.
def admitted(rgb, alpha, arg1, arg2):
    return rgb == 15 and alpha in (7, 8) and arg1 == 2 and arg2 in (3, 0x13)
assert sum(admitted(*args) for args in product(
    (14, 15, 16), (6, 7, 8, 9), (2, 3, 0x12), (2, 3, 0x13, 0x23))) == 4

cases = clamped = 0
for tex_a, diffuse_rgb, factor_byte, factor_inverted, signed2x in product(
        (0., .13, .5, .87, 1.), (0., .25, .75, 1.),
        range(256), (False, True), (False, True)):
    f = factor_byte / 255.
    if factor_inverted:
        f = 1. - f
    ref_a = min(1., max(0., (tex_a + f - .5) * (2. if signed2x else 1.)))
    native_a = min(1., max(0., (2. * (tex_a + f - .5)) if signed2x
                            else tex_a + f - .5))
    assert abs(ref_a - native_a) < 1.e-12
    rgb = min(1., .3 + diffuse_rgb * (1. - tex_a))
    assert 0. <= rgb <= 1. and 0. <= native_a <= 1.
    if (tex_a + f - .5) * (2. if signed2x else 1.) > 1.:
        clamped += 1
    cases += 1
assert clamped > 0 and cases == 5 * 4 * 256 * 2 * 2
print(f"00639 PM signed factor stage0/native Draw graph, {cases} numeric cases PASS; HMD UNTESTED")
