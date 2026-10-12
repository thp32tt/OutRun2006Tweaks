#!/usr/bin/env python3
"""Exact D3D9 PM RGB + independent ADDSIGNED2X alpha in live native Draw."""
from pathlib import Path
from itertools import product

src=(Path(__file__).resolve().parents[1]/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
flag="blendTextureAlphaPMAddSigned2XAlpha"
ps="blendTextureAlphaPmAddSigned2XAlphaPs"
code="blendTexturePmAddSigned2XAlphaCode"
fn="PSTextureBlendTextureAlphaPMAddSigned2XAlpha"
rgb="saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a))"
alpha="saturate(2.0f * (t.a + v.diffuse.a - 0.5f))"
pred=("const bool "+flag+" = op == D3DTOP_BLENDTEXTUREALPHAPM &&\n"
      "            alphaOp == D3DTOP_ADDSIGNED2X && alphaArg1 == D3DTA_TEXTURE &&\n"
      "            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);")
def linked(s):
    header="float4 "+fn+"(VOut v) : SV_Target {"
    if header not in s:
        return False
    frag=s.split(header,1)[1].split("}",1)[0]
    required=(pred,"bool "+flag+" = false;","ComPtr<ID3D11PixelShader> "+ps+";",
        "s."+ps+" &&","s."+ps+".GetAddressOf()",
        'compile("'+fn+'", "ps_4_0", '+code+')',
        "capture."+flag+" = "+flag+";",
        "capture."+flag+" ? s."+ps+".Get() :",
        "!"+flag+" &&",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"')
    return (all(x in s for x in required) and rgb in frag and alpha in frag
            and "AlphaGate(c.a); return c;" in frag
            and s.count("s."+ps+".Reset();")==2)
assert linked(src), "Missing PM_SIGNED2X game capture, native shader or draw link"
for a,b in (("D3DTOP_ADDSIGNED2X","D3DTOP_ADDSIGNED"),
            ("alphaArg1 == D3DTA_TEXTURE","alphaArg1 == D3DTA_DIFFUSE"),
            ("alphaArg2 == D3DTA_CURRENT","alphaArg2 == D3DTA_TFACTOR")):
    assert not linked(src.replace(pred,pred.replace(a,b),1)),a
for token in ("bool "+flag+" = false;","capture."+flag+" = "+flag+";",
              "capture."+flag+" ? s."+ps+".Get() :",
              "s."+ps+" &&"):
    assert not linked(src.replace(token,"BROKEN_00626",1)),token
header="float4 "+fn+"(VOut v) : SV_Target {"
fragment=header+src.split(header,1)[1].split("}",1)[0]+"}"
for token in (rgb,alpha,"AlphaGate(c.a); return c;"):
    assert not linked(src.replace(fragment,fragment.replace(token,"0.0f",1),1)),token
for tr,dr,ta,da in product((0.,.2,.6,1.),repeat=4):
    c=min(1.,tr+dr*(1.-ta))
    a=min(1.,max(0.,2*(ta+da-0.5)))
    assert 0<=c<=1 and 0<=a<=1
    if ta==da==1.: assert a==1.
    if ta==da==0.: assert a==0.
print("00626 live PM_SIGNED2X capture/shader/draw graph, destructive mutations and 256 numeric cases PASS; runtime UNTESTED")
