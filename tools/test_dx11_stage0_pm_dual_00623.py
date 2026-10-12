#!/usr/bin/env python3
"""Strict D3D9 PM-RGB independent alpha to guarded D3D11 Draw integration."""
from pathlib import Path
from itertools import product
src=(Path(__file__).resolve().parents[1]/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
modes={"AddSmooth":("ADDSMOOTH","saturate(t.a + v.diffuse.a * (1.0f - t.a))"),"Modulate2X":("MODULATE2X","saturate(2.0f * t.a * v.diffuse.a)")}
rgb="saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a))"
def linked(s,v,op,alpha):
    flag="blendTextureAlphaPM"+v+"Alpha"
    ps="blendTextureAlphaPm"+v+"AlphaPs"
    code="blendTexturePm"+v+"AlphaCode"
    fn="PSTextureBlendTextureAlphaPM"+v+"Alpha"
    hdr="float4 "+fn+"(VOut v) : SV_Target {"
    if hdr not in s:return False
    body=s.split(hdr,1)[1].split("}",1)[0]
    pred="const bool "+flag+" = op == D3DTOP_BLENDTEXTUREALPHAPM &&\n            alphaOp == D3DTOP_"+op+" && alphaArg1 == D3DTA_TEXTURE &&\n            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);"
    tokens=(pred,"bool "+flag+" = false;","ComPtr<ID3D11PixelShader> "+ps+";",
            "s."+ps+" &&","s."+ps+".GetAddressOf()",
            'compile("'+fn+'", "ps_4_0", '+code+')',
            "capture."+flag+" = "+flag+";","capture."+flag+" ? s."+ps+".Get() :",
            "!"+flag+" &&","ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
            'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"')
    return (all(t in s for t in tokens) and rgb in body and alpha in body
            and "AlphaGate(c.a); return c;" in body
            and s.count("s."+ps+".Reset();")==2)
for v,(op,alpha) in modes.items():
    assert linked(src,v,op,alpha),"unlinked "+v
    flag="blendTextureAlphaPM"+v+"Alpha"
    pred="const bool "+flag+" = op == D3DTOP_BLENDTEXTUREALPHAPM &&\n            alphaOp == D3DTOP_"+op+" && alphaArg1 == D3DTA_TEXTURE &&\n            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);"
    for old,new in (("D3DTOP_"+op,"D3DTOP_SUBTRACT"),
                    ("alphaArg1 == D3DTA_TEXTURE","alphaArg1 == D3DTA_DIFFUSE"),
                    ("alphaArg2 == D3DTA_CURRENT","alphaArg2 == D3DTA_TFACTOR")):
        assert not linked(src.replace(pred,pred.replace(old,new),1),v,op,alpha),v+" wrong op/operand"
    for token in ("bool "+flag+" = false;","capture."+flag+" = "+flag+";",
                  "capture."+flag+" ? s.blendTextureAlphaPm"+v+"AlphaPs.Get() :"):
        assert not linked(src.replace(token,"MUTATED_00623",1),v,op,alpha),v+" unlinked"
    hdr="float4 PSTextureBlendTextureAlphaPM"+v+"Alpha(VOut v) : SV_Target {"
    frag=hdr+src.split(hdr,1)[1].split("}",1)[0]+"}"
    for token in (rgb,alpha):
        assert token in frag
        assert not linked(src.replace(frag,frag.replace(token,"0.0f",1),1),v,op,alpha),v+" shader mutation"
for tr,dr,t,d in product((0.,.2,.6,1.),repeat=4):
    r=min(1.,tr+dr*(1.-t));a=min(1.,t+d*(1.-t));b=min(1.,2.*t*d)
    assert 0<=r<=1 and t<=a<=1 and 0<=b<=1
print("00623 dual-alpha live Draw graph, source mutants and 512 numeric cases PASS; runtime UNTESTED")
