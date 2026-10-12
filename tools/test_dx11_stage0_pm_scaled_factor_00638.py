#!/usr/bin/env python3
"""00638: live game PM RGB plus scaled TEXTURE*TFACTOR alpha, DX9Ex fallback."""
from itertools import product
from pathlib import Path

source = (Path(__file__).resolve().parents[1] /
          "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
pred = """const bool blendTextureAlphaPMScaledFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            (alphaOp == D3DTOP_MODULATE2X || alphaOp == D3DTOP_MODULATE4X) &&
            alphaArg1 == D3DTA_TEXTURE && alphaArg2 == D3DTA_TFACTOR;"""
inverse = """const bool blendTextureAlphaPMScaledInverseFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            (alphaOp == D3DTOP_MODULATE2X || alphaOp == D3DTOP_MODULATE4X) &&
            alphaArg1 == D3DTA_TEXTURE &&
            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT);"""
shader = """float4 PSTextureBlendTextureAlphaPMModulateFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      saturate(t.a * alphaParams.w));
    AlphaGate(c.a); return c;
}"""
graph = (
    pred, inverse,
    "if ((blendTextureAlphaPMScaledFactorAlpha ||\n             blendTextureAlphaPMScaledInverseFactorAlpha) &&\n            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))",
    "if ((blendTextureAlphaPMScaledFactorAlpha ||\n             blendTextureAlphaPMScaledInverseFactorAlpha) && !arg2Diffuse) return false;",
    "!blendTextureAlphaPMScaledFactorAlpha &&",
    "!blendTextureAlphaPMScaledInverseFactorAlpha &&",
    "capture.blendTextureAlphaPMModulateFactorAlpha = true;",
    "capture.blendFactorAlphaValue *=\n                alphaOp == D3DTOP_MODULATE2X ? 2.0f : 4.0f;",
    shader,
    "capture.blendTextureAlphaPMModulateFactorAlpha ? s.blendTextureAlphaPmModulateFactorAlphaPs.Get() :",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    "OUTRUN_DX11_FIRST_GAME_FRAME",
)
def connected(s):
    if not all(part in s for part in graph):
        return False
    return (s.index(pred) < s.index(graph[2]) < s.index(graph[3]) <
            s.index(graph[6]) < s.index(graph[7]) < s.index(graph[9]))
assert connected(source), "D3D9 state -> factor read -> scaled PS constant -> native Draw disconnected"
for part in (pred, inverse, graph[2], graph[3], graph[4], graph[5],
             graph[7], shader, graph[9], graph[10], graph[11]):
    assert not connected(source.replace(part, "BROKEN_00638", 1)), part[:75]
for old, new in (
    ("D3DTOP_BLENDTEXTUREALPHAPM", "D3DTOP_BLENDTEXTUREALPHA"),
    ("D3DTOP_MODULATE2X || alphaOp == D3DTOP_MODULATE4X",
     "D3DTOP_MODULATE || alphaOp == D3DTOP_ADD"),
    ("alphaArg1 == D3DTA_TEXTURE", "alphaArg1 == D3DTA_TFACTOR"),
    ("alphaArg2 == D3DTA_TFACTOR", "alphaArg2 == D3DTA_TEXTURE"),
):
    assert not connected(source.replace(pred, pred.replace(old, new), 1))
# D3D9: PM=15, MODULATE2X=5, MODULATE4X=6; complement=0x10.
def admitted(rgb, alpha, arg1, arg2):
    return (rgb == 15 and alpha in (5, 6) and arg1 == 2 and
            arg2 in (3, 0x13))
assert sum(admitted(*c) for c in product((14, 15), (4, 5, 6, 7),
                                         (2, 3, 0x12), (2, 3, 0x13, 0x23))) == 4
cases = 0
clamped = 0
for texture_a, vertex_rgb, factor_byte, scale, complement in product(
        (0., .2, .5, .8, 1.), (0., .25, .75, 1.),
        range(256), (2., 4.), (False, True)):
    factor = factor_byte / 255.
    constant = (1. - factor if complement else factor) * scale
    native_alpha = min(1., max(0., texture_a * constant))
    reference_alpha = min(1., texture_a * scale *
                          (1. - factor if complement else factor))
    assert abs(native_alpha - reference_alpha) < 1.e-12
    texture_rgb = .3
    native_rgb = min(1., texture_rgb + vertex_rgb * (1. - texture_a))
    assert 0. <= native_rgb <= 1. and 0. <= native_alpha <= 1.
    if texture_a * constant > 1.:
        clamped += 1
    cases += 1
assert clamped > 0 and cases == 5 * 4 * 256 * 2 * 2
print(f"00638 PM scaled factor native Draw graph, {cases} numeric cases PASS; HMD UNTESTED")
