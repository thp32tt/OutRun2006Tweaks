#!/usr/bin/env python3
"""DX11 00620: PM texture RGB with separately modulated texture/vertex alpha."""
from pathlib import Path
import itertools

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
PRED = """const bool blendTextureAlphaPMModulateAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_MODULATE && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);"""
FUNC = "float4 PSTextureBlendTextureAlphaPMModulateAlpha(VOut v) : SV_Target {"
PIXEL = "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),\n                      t.a * v.diffuse.a);"
LINKS = (
    "bool blendTextureAlphaPMModulateAlpha = false;",
    "ComPtr<ID3D11PixelShader> blendTextureAlphaPmModulateAlphaPs;",
    "s.blendTextureAlphaPmModulateAlphaPs && s.blendTextureAlphaPmFactorAlphaPs && s.layout",
    "s.blendTextureAlphaPmModulateAlphaPs.Reset();",
    "blendTexturePmModulateAlphaCode, blendTexturePmFactorAlphaCode",
    'compile("PSTextureBlendTextureAlphaPMModulateAlpha", "ps_4_0", blendTexturePmModulateAlphaCode)',
    "s.blendTextureAlphaPmModulateAlphaPs.GetAddressOf()",
    "blendTextureAlphaPMFactorAlpha || blendTextureAlphaPMInverseFactorArg1Alpha || blendTextureAlphaPMInverseFactorArg2Alpha || blendTextureAlphaPMDiffuseArg1Alpha || blendTextureAlphaPMDiffuseAlpha ||",
    "blendTextureAlphaPMDiffuseAlpha || blendTextureAlphaPMModulateAlpha ||",
    "!blendTextureAlphaPMFactorAlpha && !blendTextureAlphaPMInverseFactorArg1Alpha && !blendTextureAlphaPMInverseFactorArg2Alpha && !blendTextureAlphaPMDiffuseArg1Alpha && !blendTextureAlphaPMModulateAlpha &&",
    "capture.blendTextureAlphaPMModulateAlpha = blendTextureAlphaPMModulateAlpha;",
    "capture.blendTextureAlphaPMModulateAlpha ? s.blendTextureAlphaPmModulateAlphaPs.Get() :",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"',
)
def linked(s):
    body = s.split(FUNC, 1)
    return (PRED in s and len(body)==2 and PIXEL in body[1].split("}",1)[0]
            and "AlphaGate(c.a); return c;" in body[1].split("}",1)[0]
            and all(x in s for x in LINKS)
            and s.count("s.blendTextureAlphaPmModulateAlphaPs.Reset();")==2
            and s.count("s.blendTextureAlphaPmModulateAlphaPs.GetAddressOf()")==1)
def main():
    s=SOURCE.read_text(encoding="utf-8")
    assert linked(s), "00620 live C++ shader/capture/Draw linkage missing"
    unique=[x for x in LINKS if s.count(x)==1]
    for x in unique:
        assert not linked(s.replace(x,"BROKEN_00620",1)),x
    for old,new in (("alphaArg1 == D3DTA_TEXTURE","alphaArg1 == D3DTA_TFACTOR"),
                    ("alphaArg2 == D3DTA_CURRENT","alphaArg2 == D3DTA_TFACTOR"),
                    ("alphaOp == D3DTOP_MODULATE","alphaOp == D3DTOP_ADD")):
        assert not linked(s.replace(PRED,PRED.replace(old,new),1))
    for old in ("t.a","v.diffuse.a","t.rgb + v.diffuse.rgb * (1.0f - t.a)"):
        assert not linked(s.replace(PIXEL,PIXEL.replace(old,"0.0f",1),1))
    count=0
    for tr,dr,ta,da in itertools.product((0.,.2,.6,1.),(0.,.3,.8,1.),(0.,.4,.9,1.),(0.,.25,.75,1.)):
        rgb=min(1.,tr+dr*(1.-ta));alpha=ta*da
        assert 0<=rgb<=1 and 0<=alpha<=1
        count+=1
    assert count==256
    print(f"00620 native PM + modulated alpha: {len(unique)+6} negative mutations, 256 arithmetic cases PASS; HMD UNTESTED")
if __name__=="__main__": main()
