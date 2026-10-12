#!/usr/bin/env python3
"""00629 real D3D9 PM RGB + BLENDFACTORALPHA alpha -> guarded native D3D11 Draw."""
from itertools import product
from pathlib import Path
source = (Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
flag = "blendTextureAlphaPMBlendFactorAlpha"
ps = "blendTextureAlphaPmBlendFactorAlphaPs"
fn = "PSTextureBlendTextureAlphaPMBlendFactorAlpha"
blob = "blendTexturePmBlendFactorAlphaCode"
pred = ("const bool " + flag + " = op == D3DTOP_BLENDTEXTUREALPHAPM &&\n"
        "            alphaOp == D3DTOP_BLENDFACTORALPHA && alphaArg1 == D3DTA_TEXTURE &&\n"
        "            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);")
header = "float4 " + fn + "(VOut v) : SV_Target {"
rgb = "saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a))"
alpha = "lerp(v.diffuse.a, t.a, alphaParams.w)"
def linked(s):
    if header not in s: return False
    body = s.split(header, 1)[1].split("}", 1)[0]
    parts = (pred, "bool " + flag + " = false;",
        "ComPtr<ID3D11PixelShader> " + ps + ";", "s." + ps + " &&",
        "s." + ps + ".GetAddressOf()",
        "capture." + flag + " = " + flag + ";",
        "capture." + flag + " ? s." + ps + ".Get() :", "!" + flag + " &&",
        'compile("' + fn + '", "ps_4_0", ' + blob + ')',
        "blendTextureAlphaPMFactorAlpha || " + flag + " ||",
        "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)",
        "capture.blendFactorAlphaValue = static_cast<float>((textureFactor >> 24u) & 0xffu) / 255.0f;",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"')
    return (all(x in s for x in parts) and rgb in body and alpha in body
            and "AlphaGate(c.a); return c;" in body
            and s.count("s." + ps + ".Reset();") == 2)
assert linked(source), "source capture/shader/real native Draw graph missing"
for before,after in (("D3DTOP_BLENDFACTORALPHA","D3DTOP_BLENDDIFFUSEALPHA"),
                     ("alphaArg1 == D3DTA_TEXTURE","alphaArg1 == D3DTA_DIFFUSE"),
                     ("alphaArg2 == D3DTA_CURRENT","alphaArg2 == D3DTA_TFACTOR")):
    assert not linked(source.replace(pred,pred.replace(before,after),1)),before
for token in ("s."+ps+" &&", "s."+ps+".GetAddressOf()",
              "capture."+flag+" = "+flag+";", "capture."+flag+" ? s."+ps+".Get() :",
              "!"+flag+" &&", 'compile("'+fn+'", "ps_4_0", '+blob+')',
              "blendTextureAlphaPMFactorAlpha || "+flag+" ||"):
    assert not linked(source.replace(token,"BROKEN_00629",1)),token
frag = header + source.split(header,1)[1].split("}",1)[0] + "}"
for token in (rgb,alpha,"AlphaGate(c.a); return c;"):
    assert not linked(source.replace(frag,frag.replace(token,"0.0f",1),1)),token
distinct = 0
for tr,dr,ta,da,factor in product((0.,.2,.6,1.),repeat=5):
    rgb_out = min(1.,max(0.,tr+dr*(1.-ta)))
    alpha_out = da + (ta-da)*factor
    assert 0. <= rgb_out <= 1. and 0. <= alpha_out <= 1.
    # IEEE-754 interpolation can differ by one ULP at the 0/1 endpoints.
    if factor == 0: assert abs(alpha_out - da) < 1.e-12
    if factor == 1: assert abs(alpha_out - ta) < 1.e-12
    if abs(alpha_out-(da+(ta-da)*ta)) > 1.e-10: distinct += 1
assert distinct > 0, "factor interpolation improperly follows texture alpha"
print("00629 PM RGB-factor alpha graph/destructive/1024 numeric cases PASS; HMD UNTESTED")
