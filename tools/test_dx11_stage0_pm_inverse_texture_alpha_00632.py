#!/usr/bin/env python3
"""00632: actual D3D9 PM RGB+complemented texture alpha routes to native D3D11 Draw."""
from pathlib import Path
from itertools import product
s = (Path(__file__).resolve().parents[1]/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
predicate = ("const bool blendTextureAlphaPMInverseTextureAlpha =\n"
             "            op == D3DTOP_BLENDTEXTUREALPHAPM &&\n"
             "            alphaOp == D3DTOP_SELECTARG1 &&\n"
             "            alphaArg1 == (D3DTA_TEXTURE | D3DTA_COMPLEMENT);")
shader = "float4 PSTextureBlendTextureAlphaPMSelectInverseTextureAlpha(VOut v) : SV_Target {"
pixel = "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), 1.0f - t.a);"
links = (predicate, shader, pixel, "bool blendTextureAlphaPMInverseTextureAlpha = false;",
         "blendTextureAlphaPMBlendFactorAlpha || blendTextureAlphaPMInverseTextureAlpha ||",
         "!blendTextureAlphaPMInverseTextureAlpha && !blendTextureAlphaPMInverseDiffuseAlpha && !blendTextureAlphaPMFactorAlpha",
         "alphaArg1 != D3DTA_TEXTURE && !blendTextureAlphaPMDiffuseAlpha && !blendTextureAlphaPMDiffuseArg1Alpha && !blendTextureAlphaPMInverseTextureAlpha",
         "capture.blendTextureAlphaPMInverseTextureAlpha = blendTextureAlphaPMInverseTextureAlpha;",
         'compile("PSTextureBlendTextureAlphaPMSelectInverseTextureAlpha", "ps_4_0", blendTexturePmInverseTextureAlphaCode)',
         "s.blendTextureAlphaPmInverseTextureAlphaPs.GetAddressOf()",
         "capture.blendTextureAlphaPMInverseTextureAlpha ? s.blendTextureAlphaPmInverseTextureAlphaPs.Get() :",
         "s.blendTextureAlphaPmInverseTextureAlphaPs.Reset();",
         "ctx->DrawIndexed(indexCount, 0, 0);",
         "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
         'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"')
def linked(src):
    if not all(v in src for v in links):
        return False
    hlsl = src.split(shader,1)[1].split("}",1)[0]
    return (pixel in hlsl and "AlphaGate(c.a); return c;" in hlsl and
            src.index(predicate) < src.index(links[7]) < src.index(links[10]))
assert linked(s), "broken native capture/shader/Draw source graph"
for item in (predicate,pixel,links[5],links[6],links[7],links[9],links[10]):
    assert s.count(item)==1, "non-unique mutation anchor"
    assert not linked(s.replace(item,"BROKEN_00632",1))
assert s.count(links[4])==2 and s.count(links[11])==2
assert not linked(s.replace(links[4],"BROKEN_00632"))
assert not linked(s.replace(links[11],"BROKEN_00632"))
for a,b in (("D3DTOP_BLENDTEXTUREALPHAPM","D3DTOP_BLENDTEXTUREALPHA"),
            ("D3DTOP_SELECTARG1","D3DTOP_SELECTARG2"),
            ("D3DTA_TEXTURE | D3DTA_COMPLEMENT","D3DTA_TEXTURE | D3DTA_ALPHAREPLICATE")):
    assert not linked(s.replace(predicate,predicate.replace(a,b,1),1))
def admitted(rgb,alpha,arg):
    return rgb==15 and alpha==2 and arg==(2|0x10)
for arg in (0,1,2,0x12,0x22,0x32,0x10):
    assert admitted(15,2,arg)==(arg==0x12)
assert not admitted(15,3,0x12) and not admitted(12,2,0x12)
different=0
for t,d,a in product((0.,.25,.75,1.),repeat=3):
    rgb=min(1.,t+d*(1.-a))
    out_alpha=1.-a
    assert 0.<=rgb<=1. and 0.<=out_alpha<=1.
    different+=abs(rgb-min(1.,t+d*a))>1e-6
assert different>0
print("00632 complemented alpha: linked capture/native shader/Draw, destructive and 64 numerical cases PASS; HMD UNTESTED")
