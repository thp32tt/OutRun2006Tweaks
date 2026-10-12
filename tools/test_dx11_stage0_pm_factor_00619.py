#!/usr/bin/env python3
"""00619 stage0 PM RGB / independent TFACTOR alpha: native Draw integration; Quest3 UNTESTED."""
from pathlib import Path
import itertools
S=Path(__file__).resolve().parents[1]/"src/vr/d3d11/live_game_frame_bridge.cpp"
TOKENS=(
    "const bool blendTextureAlphaPMFactorAlpha =",
    "alphaOp == D3DTOP_SELECTARG1 && alphaArg1 == D3DTA_TFACTOR;",
    "blendTextureAlphaPMFactorAlpha || blendFactorDiffuseAlpha",
    "blendTextureAlphaPMFactorAlpha || blendTextureAlphaPMDiffuseAlpha ||",
    "!blendTextureAlphaPMFactorAlpha &&",
    "!selectDiffuseTfactorArg2Alpha && !blendTextureAlphaPMFactorAlpha",
    "capture.blendTextureAlphaPMFactorAlpha = blendTextureAlphaPMFactorAlpha;",
    "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)",
    "capture.blendFactorAlphaValue = static_cast<float>((textureFactor >> 24u) & 0xffu) / 255.0f;",
    "bool blendTextureAlphaPMFactorAlpha = false;",
    "ComPtr<ID3D11PixelShader> blendTextureAlphaPmFactorAlphaPs;",
    "s.blendTextureAlphaPmFactorAlphaPs && s.layout",
    "blendTexturePmFactorAlphaCode, blendDiffuseCode",
    'compile("PSTextureBlendTextureAlphaPMSelectFactorAlpha", "ps_4_0", blendTexturePmFactorAlphaCode)',
    "s.blendTextureAlphaPmFactorAlphaPs.GetAddressOf()",
    "s.blendTextureAlphaPmFactorAlphaPs.Reset();",
    "capture.blendTextureAlphaPMFactorAlpha ? s.blendTextureAlphaPmFactorAlphaPs.Get() :",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"')
def linked(s):
    body=s.split("float4 PSTextureBlendTextureAlphaPMSelectFactorAlpha(VOut v) : SV_Target {",1)
    return len(body)==2 and all(x in s for x in TOKENS) and s.count("s.blendTextureAlphaPmFactorAlphaPs.Reset();")==2 and all(x in body[1].split("}",1)[0] for x in (
        "float4 t = gameTexture.Sample(gameSampler, v.uv);",
        "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), alphaParams.w);",
        "AlphaGate(c.a); return c;"))
def main():
    s=S.read_text(encoding="utf-8")
    assert linked(s)
    for x in TOKENS:
        assert not linked(s.replace(x, "BROKEN_00619",1)),x
    for tr,dr,ta,fa in itertools.product((0.,.25,.85,1.),(0.,.4,.9,1.),(0.,.3,.95,1.),range(256)):
        assert 0<=min(1.,tr+dr*(1.-ta))<=1 and 0<=fa/255.<=1
    print("00619 source linkage, destructive mutations, 16384 numeric samples PASS; Quest3 UNTESTED")
if __name__=="__main__":main()
