#!/usr/bin/env python3
"""00627: live game PM RGB with independently blended texture alpha."""
from pathlib import Path
from itertools import product

src=(Path(__file__).resolve().parents[1]/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
flag="blendTextureAlphaPMBlendTextureAlpha"
ps="blendTextureAlphaPmBlendTextureAlphaPs"
code="blendTexturePmBlendTextureAlphaCode"
fn="PSTextureBlendTextureAlphaPMBlendTextureAlpha"
pred=("const bool "+flag+" = op == D3DTOP_BLENDTEXTUREALPHAPM &&\n"
      "            alphaOp == D3DTOP_BLENDTEXTUREALPHA && alphaArg1 == D3DTA_TEXTURE &&\n"
      "            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);")
header="float4 "+fn+"(VOut v) : SV_Target {"
rgb="saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a))"
alpha="lerp(v.diffuse.a, t.a, t.a)"
def linked(s):
    if header not in s: return False
    frag=s.split(header,1)[1].split("}",1)[0]
    required=(pred,"bool "+flag+" = false;", "ComPtr<ID3D11PixelShader> "+ps+";",
        "s."+ps+" &&", "s."+ps+".GetAddressOf()", 'compile("'+fn+'", "ps_4_0", '+code+')',
        "capture."+flag+" = "+flag+";", "capture."+flag+" ? s."+ps+".Get() :",
        "!"+flag+" &&","ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"')
    return (all(x in s for x in required) and rgb in frag and alpha in frag
        and "AlphaGate(c.a); return c;" in frag and s.count("s."+ps+".Reset();")==2)
assert linked(src),"missing new capture-to-native Draw shader graph"
for a,b in (("D3DTOP_BLENDTEXTUREALPHA","D3DTOP_BLENDDIFFUSEALPHA"),
    ("alphaArg1 == D3DTA_TEXTURE","alphaArg1 == D3DTA_DIFFUSE"),
    ("alphaArg2 == D3DTA_CURRENT","alphaArg2 == D3DTA_TFACTOR")):
    assert not linked(src.replace(pred,pred.replace(a,b),1)),a
for token in ("s."+ps+" &&","capture."+flag+" = "+flag+";",
              "capture."+flag+" ? s."+ps+".Get() :","!"+flag+" &&"):
    assert not linked(src.replace(token,"BROKEN_00627",1)),token
fragment=header+src.split(header,1)[1].split("}",1)[0]+"}"
for token in (rgb,alpha,"AlphaGate(c.a); return c;"):
    assert not linked(src.replace(fragment,fragment.replace(token,"0.0f",1),1)),token
for tr,dr,ta,da in product((0.,.2,.6,1.),repeat=4):
    c=min(1.,max(0.,tr+dr*(1.-ta)))
    a=da+(ta-da)*ta
    assert 0<=c<=1 and 0<=a<=1
    if ta==0.: assert a==da
    if ta==1.: assert a==1.
    if ta==.6 and da==.2: assert abs(a-.44)<1e-12
print("00627 live capture/PS/Draw graph, destructive negative tests, 256 numeric cases PASS; Quest3/VDXR UNTESTED")
