#!/usr/bin/env python3
"""Live PM RGB ADD / ADDSMOOTH TFACTOR alpha, exact source and native-PS regressions."""
from pathlib import Path
from itertools import product
s=(Path(__file__).resolve().parents[1]/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
add="""const bool blendTextureAlphaPMAddFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM && alphaOp == D3DTOP_ADD &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_TFACTOR ||
             alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT));"""
smooth="""const bool blendTextureAlphaPMAddSmoothFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM && alphaOp == D3DTOP_ADDSMOOTH &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_TFACTOR ||
             alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT));"""
graph=[
    add,smooth,
    "float4 PSTextureBlendTextureAlphaPMAddFactorAlpha(VOut v) : SV_Target {",
    "float4 PSTextureBlendTextureAlphaPMAddSmoothFactorAlpha(VOut v) : SV_Target {",
    "saturate(t.a + alphaParams.w));",
    "saturate(t.a + alphaParams.w * (1.0f - t.a)));",
    "if ((blendTextureAlphaPMAddFactorAlpha ||\n             blendTextureAlphaPMAddSmoothFactorAlpha) &&\n            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))",
    "if ((blendTextureAlphaPMAddFactorAlpha ||\n             blendTextureAlphaPMAddSmoothFactorAlpha) && !arg2Diffuse) return false;",
    "!blendTextureAlphaPMAddFactorAlpha &&\n              !blendTextureAlphaPMAddSmoothFactorAlpha &&",
    "capture.blendTextureAlphaPMAddFactorAlpha = blendTextureAlphaPMAddFactorAlpha;",
    "capture.blendTextureAlphaPMAddSmoothFactorAlpha = blendTextureAlphaPMAddSmoothFactorAlpha;",
    "if ((blendTextureAlphaPMAddFactorAlpha ||\n             blendTextureAlphaPMAddSmoothFactorAlpha) &&\n            (alphaArg2 & D3DTA_COMPLEMENT) != 0u)\n            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;",
    'compile("PSTextureBlendTextureAlphaPMAddFactorAlpha", "ps_4_0", blendTexturePmAddFactorCode)',
    'compile("PSTextureBlendTextureAlphaPMAddSmoothFactorAlpha", "ps_4_0", blendTexturePmAddSmoothFactorCode)',
    "s.blendTextureAlphaPmAddFactorAlphaPs.GetAddressOf()",
    "s.blendTextureAlphaPmAddSmoothFactorAlphaPs.GetAddressOf()",
    "capture.blendTextureAlphaPMAddFactorAlpha ? s.blendTextureAlphaPmAddFactorAlphaPs.Get() :",
    "capture.blendTextureAlphaPMAddSmoothFactorAlpha ? s.blendTextureAlphaPmAddSmoothFactorAlphaPs.Get() :",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"]
assert "OUTRUN_DX11_FIRST_GAME_FRAME" in s
def connected(x):
    return all(t in x for t in graph) and x.index(add)<x.index(graph[6])<x.index(graph[7])<x.index(graph[9])<x.index(graph[16])<x.index(graph[18])
assert connected(s)
for token in graph:
    assert not connected(s.replace(token,"REMOVED_00640",1)),token[:75]
for pred in (add,smooth):
    for a,b in (("D3DTOP_BLENDTEXTUREALPHAPM","D3DTOP_BLENDTEXTUREALPHA"),("alphaArg1 == D3DTA_TEXTURE","alphaArg1 == D3DTA_TFACTOR"),("alphaArg2 == D3DTA_TFACTOR","alphaArg2 == D3DTA_TEXTURE")):
        assert not connected(s.replace(pred,pred.replace(a,b),1))
def allowed(op,a1,a2):return op in (7,11) and a1==2 and a2 in (3,19)
assert sum(allowed(*q) for q in product((7,8,11),(2,3,18),(2,3,19,35)))==4
n=0
for t,drgb,fb,inv,op in product((0.,.13,.5,.87,1.),(0.,.25,.75,1.),range(256),(False,True),("ADD","ADDSMOOTH")):
    f=fb/255.
    if inv:f=1.-f
    ref=min(1.,t+(f if op=="ADD" else f*(1.-t)))
    actual=min(1.,max(0.,t+(f if op=="ADD" else f*(1.-t))))
    assert abs(ref-actual)<1e-12
    rgb=min(1.,.3+drgb*(1.-t))
    assert 0.<=rgb<=1. and 0.<=actual<=1.
    n+=1
assert n==20480
print("00640 PM factor ADD/ADDSMOOTH native Draw graph + 20480 numeric PASS; HMD UNTESTED")
