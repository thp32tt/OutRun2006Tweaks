#!/usr/bin/env python3
"""00628 native game PM RGB and independently diffuse-weighted alpha."""
from pathlib import Path
from itertools import product

source = (Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
flag = "blendTextureAlphaPMBlendDiffuseAlpha"
ps = "blendTextureAlphaPmBlendDiffuseAlphaPs"
blob = "blendTexturePmBlendDiffuseAlphaCode"
fn = "PSTextureBlendTextureAlphaPMBlendDiffuseAlpha"
pred = ("const bool " + flag + " = op == D3DTOP_BLENDTEXTUREALPHAPM &&\n"
        "            alphaOp == D3DTOP_BLENDDIFFUSEALPHA && alphaArg1 == D3DTA_TEXTURE &&\n"
        "            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);")
header = "float4 " + fn + "(VOut v) : SV_Target {"
rgb = "saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a))"
alpha = "lerp(v.diffuse.a, t.a, v.diffuse.a)"

def linked(s):
    if header not in s: return False
    frag = s.split(header,1)[1].split("}",1)[0]
    parts = (
        pred, "bool " + flag + " = false;",
        "ComPtr<ID3D11PixelShader> " + ps + ";", "s." + ps + " &&",
        "s." + ps + ".GetAddressOf()", "capture." + flag + " = " + flag + ";",
        "capture." + flag + " ? s." + ps + ".Get() :", "!" + flag + " &&",
        'compile("' + fn + '", "ps_4_0", ' + blob + ')',
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"')
    return (all(x in s for x in parts) and rgb in frag and alpha in frag
            and "AlphaGate(c.a); return c;" in frag
            and s.count("s." + ps + ".Reset();") == 2)

assert linked(source), "D3D9 PM RGB/diffuse alpha -> DX11 Draw graph missing"
for before, after in (
    ("D3DTOP_BLENDDIFFUSEALPHA","D3DTOP_BLENDTEXTUREALPHA"),
    ("alphaArg1 == D3DTA_TEXTURE","alphaArg1 == D3DTA_DIFFUSE"),
    ("alphaArg2 == D3DTA_CURRENT","alphaArg2 == D3DTA_TFACTOR")
):
    assert not linked(source.replace(pred,pred.replace(before,after),1)),before
for token in (
    "s." + ps + " &&", "s." + ps + ".GetAddressOf()",
    "capture." + flag + " = " + flag + ";",
    "capture." + flag + " ? s." + ps + ".Get() :",
    "!" + flag + " &&", 'compile("' + fn + '", "ps_4_0", ' + blob + ')'
):
    assert not linked(source.replace(token,"BROKEN_00628",1)),token
frag = header + source.split(header,1)[1].split("}",1)[0] + "}"
for token in (rgb,alpha,"AlphaGate(c.a); return c;"):
    assert not linked(source.replace(frag,frag.replace(token,"0.0f",1),1)),token
distinct = 0
for tr,dr,ta,da in product((0.,.2,.6,1.),repeat=4):
    c = min(1.,max(0.,tr+dr*(1.-ta)))
    a = da + (ta-da)*da
    assert 0. <= c <= 1. and 0. <= a <= 1.
    if da == 0.: assert a == 0.
    if da == 1.: assert abs(a-ta) < 1.e-12
    if abs(a - (da+(ta-da)*ta)) > 1.e-10: distinct += 1
assert distinct > 0, "diffuse alpha and texture alpha weighting wrongly aliased"
print("00628 native PM/diffuse alpha source-to-Draw, destructive and 256 numeric cases PASS; HMD UNTESTED")
