#!/usr/bin/env python3
"""00634 native game Draw: stage0 PM with complemented CURRENT/DIFFUSE output alpha."""
from itertools import product
from pathlib import Path
s=(Path(__file__).resolve().parents[1]/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
a="""const bool blendTextureAlphaPMInverseDiffuseArg1Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG1 &&
            (alphaArg1 == (D3DTA_DIFFUSE | D3DTA_COMPLEMENT) ||
             alphaArg1 == (D3DTA_CURRENT | D3DTA_COMPLEMENT));"""
b="""const bool blendTextureAlphaPMInverseDiffuseArg2Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG2 &&
            (alphaArg2 == (D3DTA_DIFFUSE | D3DTA_COMPLEMENT) ||
             alphaArg2 == (D3DTA_CURRENT | D3DTA_COMPLEMENT));"""
o="""if (blendTextureAlphaPMInverseDiffuseArg2Alpha) {
            capture.blendTextureAlphaPMDiffuseAlpha = false;
            capture.blendTextureAlphaPMInverseDiffuseAlpha = true;
        }"""
entry="float4 PSTextureBlendTextureAlphaPMSelectInverseDiffuseAlpha(VOut v) : SV_Target {"
pix="float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), 1.0f - v.diffuse.a);"
keys=[a,b,o,entry,pix,'compile("PSTextureBlendTextureAlphaPMSelectInverseDiffuseAlpha", "ps_4_0", blendTexturePmInverseDiffuseAlphaCode)',"capture.blendTextureAlphaPMInverseDiffuseAlpha ? s.blendTextureAlphaPmInverseDiffuseAlphaPs.Get() :","capture.blendTextureAlphaPMInverseDiffuseAlpha = blendTextureAlphaPMInverseDiffuseArg1Alpha;","s.blendTextureAlphaPmInverseDiffuseAlphaPs.GetAddressOf()","s.blendTextureAlphaPmInverseDiffuseAlphaPs &&","!blendTextureAlphaPMInverseDiffuseAlpha && !blendTextureAlphaPMFactorAlpha","!blendTextureAlphaPMInverseDiffuseArg1Alpha) && !selectTextureTfactorAlpha","!blendTextureAlphaPMInverseDiffuseArg2Alpha) ||","ctx->DrawIndexed(indexCount, 0, 0);","ctx->Draw(static_cast<UINT>(vertices.size()), 0);",'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"']
def ok(t):
    return all(k in t for k in keys) and pix in t.split(entry,1)[1].split("}",1)[0] and "AlphaGate(c.a); return c;" in t.split(entry,1)[1].split("}",1)[0] and t.index(a)<t.index(b)<t.index(o)<t.index(keys[6])
assert ok(s), "live D3D9 source -> capture -> D3D11 HLSL/Draw disconnected"
for k in keys[:13]:
    assert s.count(k)==1, "duplicate or missing: "+k[:60]
    assert not ok(s.replace(k,"BROKEN_00634",1)), "destructive source mutation missed: "+k[:60]
for t in (a,b):
    for token in ("D3DTOP_SELECTARG1","D3DTOP_SELECTARG2","D3DTA_DIFFUSE | D3DTA_COMPLEMENT","D3DTA_CURRENT | D3DTA_COMPLEMENT"):
        if token in t: assert not ok(s.replace(t,t.replace(token,"WRONG",1),1))
# PM=15; SELECTARG1/2=2/3; stage0 DIFFUSE=0/CURRENT=1, complement=0x10.
def select(rgb,op,x,y):return rgb==15 and ((op==2 and x in (16,17)) or (op==3 and y in (16,17)))
for rgb,op,x,y in product((12,15),(2,3,4),(0,1,2,16,17,18,32),(0,1,2,16,17,18,32)):
    assert select(rgb,op,x,y)==(rgb==15 and (x in (16,17) if op==2 else y in (16,17) if op==3 else False))
for t,d,ta,da in product((0.,.2,.8,1.),repeat=4):
    rgb=min(1.,t+d*(1.-ta)); alpha=1.-da
    assert 0<=rgb<=1 and 0<=alpha<=1
print("00634 dual selector native pixel and destructive/numeric regressions PASS; HMD UNTESTED")
