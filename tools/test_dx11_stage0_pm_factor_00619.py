#!/usr/bin/env python3
"""00619 stage0 PM RGB / independent TFACTOR alpha: native Draw integration; Quest3 UNTESTED."""
from pathlib import Path
import itertools
S=Path(__file__).resolve().parents[1]/"src/vr/d3d11/live_game_frame_bridge.cpp"
TOKENS=(
    "const bool blendTextureAlphaPMFactorAlpha =",
    "alphaOp == D3DTOP_SELECTARG1 && alphaArg1 == D3DTA_TFACTOR;",
    # Both independently captured TFACTOR select and factor-weighted alpha must
    # remain explicitly present in the live texture-factor read predicate.
    "blendTextureAlphaPMFactorAlpha || blendTextureAlphaPMBlendFactorAlpha || blendFactorDiffuseAlpha",
    "blendTextureAlphaPMFactorAlpha || blendTextureAlphaPMInverseFactorArg1Alpha || blendTextureAlphaPMInverseFactorArg2Alpha || blendTextureAlphaPMDiffuseArg1Alpha || blendTextureAlphaPMDiffuseAlpha ||",
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
    predicate=s.split("const bool blendTextureAlphaPMFactorAlpha =",1)
    texture_alpha=s.split("const bool blendTextureAlphaPMTextureAlpha =",1)
    texture_predicate=texture_alpha[1].split(";",1)[0] if len(texture_alpha)==2 else ""
    # The earlier texture-alpha shader must be mutually exclusive with factor
    # alpha, otherwise submit() selects its earlier branch and loses TFACTOR A.
    return (len(texture_alpha)==2 and
        "alphaArg1 == D3DTA_TEXTURE" in texture_predicate and
        len(predicate)==2 and
        "op == D3DTOP_BLENDTEXTUREALPHAPM &&" in predicate[1].split(";",1)[0] and
        "alphaOp == D3DTOP_SELECTARG1 && alphaArg1 == D3DTA_TFACTOR" in predicate[1].split(";",1)[0] and
        len(body)==2 and all(x in s for x in TOKENS) and s.count("s.blendTextureAlphaPmFactorAlphaPs.Reset();")==2 and all(x in body[1].split("}",1)[0] for x in (
        "float4 t = gameTexture.Sample(gameSampler, v.uv);",
        "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), alphaParams.w);",
        "AlphaGate(c.a); return c;")))
def main():
    s=S.read_text(encoding="utf-8")
    assert linked(s)
    # Mutate only uniquely owned links; TFACTOR-alpha is used by earlier
    # SELECTARG cases, so a global first-occurrence mutation is a false negative.
    unique_links = [x for x in TOKENS if s.count(x) == 1]
    for x in unique_links:
        assert not linked(s.replace(x, "BROKEN_00619", 1)), x
    texture_condition = ("const bool blendTextureAlphaPMTextureAlpha =\\n"
                         "            op == D3DTOP_BLENDTEXTUREALPHAPM && alphaOp == D3DTOP_SELECTARG1 &&\\n"
                         "            alphaArg1 == D3DTA_TEXTURE;").replace("\\n", "\n")
    assert texture_condition in s
    assert not linked(s.replace(texture_condition,
        texture_condition.replace("alphaArg1 == D3DTA_TEXTURE", "alphaArg1 == D3DTA_TFACTOR"), 1))
    predicate = ("const bool blendTextureAlphaPMFactorAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&\\n"
                 "            alphaOp == D3DTOP_SELECTARG1 && alphaArg1 == D3DTA_TFACTOR;")
    # Source uses a real newline; match the feature-owned predicate exactly.
    predicate = predicate.replace("\\n", "\n")
    assert predicate in s
    assert not linked(s.replace(predicate, predicate.replace("D3DTA_TFACTOR", "D3DTA_TEXTURE"), 1))
    pixel = "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), alphaParams.w);"
    assert pixel in s
    assert not linked(s.replace(pixel, "float4 c = float4(t.rgb, t.a);", 1))
    for tr,dr,ta,fa in itertools.product((0.,.25,.85,1.),(0.,.4,.9,1.),(0.,.3,.95,1.),range(256)):
        assert 0<=min(1.,tr+dr*(1.-ta))<=1 and 0<=fa/255.<=1
    print(f"00619 source linkage, {len(unique_links)+3} scoped destructive mutations, 16384 numeric samples PASS; Quest3 UNTESTED")
if __name__=="__main__":main()
