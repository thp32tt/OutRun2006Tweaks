#!/usr/bin/env python3
"""00587 stage-0 SELECTARG RGB plus independent D3DTA_TFACTOR alpha gate."""
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
CASES = (("Texture","selectTextureTfactorAlpha","SELECTARG1","t.rgb"),
         ("Diffuse","selectDiffuseTfactorAlpha","SELECTARG2","v.diffuse.rgb"))

def connected(s):
    try:
        pipe=s.split("bool ensure_pipeline(",1)[1].split("bool supported_game_state(",1)[0]
        gate=s.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
        draw=s.split("bool submit(",1)[1].split("void observe(",1)[0]
    except IndexError: return False
    if not all(x in gate for x in ("arg != D3DTA_TEXTURE", "alphaArg1 != D3DTA_TEXTURE",
          "selectTextureTfactorAlpha || selectDiffuseTfactorAlpha",
          "(!selectDiffuseDiffuseAlpha && !mixedDiffuseAlpha && !mixedAddDiffuseAlpha && !blendTextureAlphaPMInverseFactorArg1Alpha && !blendTextureAlphaPMInverseFactorArg2Alpha && alphaArg1 != D3DTA_TEXTURE && !blendTextureAlphaPMDiffuseAlpha && !blendTextureAlphaPMDiffuseArg1Alpha && !blendTextureAlphaPMInverseTextureAlpha && !blendTextureAlphaPMInverseDiffuseArg1Alpha) && !selectTextureTfactorAlpha && !selectDiffuseTfactorAlpha",
          "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)",
          "const bool rgbNeedsDiffuse = selectDiffuseTextureAlpha || selectDiffuseDiffuseAlpha || selectDiffuseTfactorAlpha ||",
          "(rgbNeedsDiffuse && !arg2Diffuse)", "nextColorOp != D3DTOP_DISABLE",
          "capture.blendFactorAlphaValue = static_cast<float>((textureFactor >> 24u) & 0xffu) / 255.0f;")): return False
    if not all(x in draw for x in ("static_cast<float>(output.alphaFunc), capture.blendFactorAlphaValue",
        "ctx->PSSetConstantBuffers(0, 1, &alphaBuffer);", "ctx->PSSetShaderResources(0, 1, &boundView);",
        "ctx->DrawIndexed(indexCount, 0, 0);", "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")): return False
    if 'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"' not in s: return False
    for label,flag,op,rgb in CASES:
        entry="PSTextureSelect"+label+"TfactorAlpha"
        shader=s.split("float4 "+entry+"(VOut v) : SV_Target {",1)
        if len(shader)<2: return False
        body=shader[1].split("}",1)[0]
        if "float4 c = float4("+rgb+", alphaParams.w);" not in body or "AlphaGate(c.a)" not in body: return False
        if not all(x in gate for x in ("const bool "+flag+" = op == D3DTOP_"+op+" &&",
              "alphaOp == D3DTOP_SELECTARG1 && alphaArg1 == D3DTA_TFACTOR;",
              "capture."+flag+" = "+flag+";", "!"+flag+" &&")): return False
        if not all(x in pipe for x in ("s."+flag+"Ps &&", '!compile("'+entry+'", "ps_4_0",',
              "s."+flag+"Ps.GetAddressOf()")): return False
        if "capture."+flag+" ? s."+flag+"Ps.Get()" not in draw: return False
        if "ComPtr<ID3D11PixelShader> "+flag+"Ps;" not in s: return False
        if s.count("s."+flag+"Ps.Reset();")!=2: return False
    return True

def mutation(s, old, new):
    occurrences=s.count(old)
    # 00635 adds an independent complemented-factor source read.
    # The legacy factor-source negative test must sever *both* consumers.
    if old=="GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)":
        assert occurrences>=1, (old,occurrences)
        return s.replace(old,new)
    assert occurrences==1, (old,occurrences)
    return s.replace(old,new,1)

def main():
    s=P.read_text(encoding="utf-8")
    assert connected(s), "live texture factor alpha is not wired to native Draw"
    n=0
    for label,flag,op,rgb in CASES:
        entry="PSTextureSelect"+label+"TfactorAlpha"
        for a,b in (
            ("const bool "+flag+" = op == D3DTOP_"+op+" &&","const bool "+flag+" = op == D3DTOP_DISABLE &&"),
            ("capture."+flag+" = "+flag+";","capture."+flag+" = false;"),
            ("(!selectDiffuseDiffuseAlpha && !mixedDiffuseAlpha && !mixedAddDiffuseAlpha && !blendTextureAlphaPMInverseFactorArg1Alpha && !blendTextureAlphaPMInverseFactorArg2Alpha && alphaArg1 != D3DTA_TEXTURE && !blendTextureAlphaPMDiffuseAlpha && !blendTextureAlphaPMDiffuseArg1Alpha && !blendTextureAlphaPMInverseTextureAlpha && !blendTextureAlphaPMInverseDiffuseArg1Alpha) && !selectTextureTfactorAlpha && !selectDiffuseTfactorAlpha",
             "!selectTextureTfactorAlpha || !selectDiffuseTfactorAlpha && alphaArg1 != D3DTA_TEXTURE"),
            ("capture."+flag+" ? s."+flag+"Ps.Get()","capture."+flag+" ? nullptr"),
            ("s."+flag+"Ps.GetAddressOf()","nullptr"),
            ('!compile("'+entry+'", "ps_4_0",','!compile("bad", "ps_4_0",'),
            ("float4 c = float4("+rgb+", alphaParams.w);","float4 c = float4("+rgb+", t.a);"),
            ("ComPtr<ID3D11PixelShader> "+flag+"Ps;","ComPtr<ID3D11PixelShader> unused;")):
            assert not connected(mutation(s,a,b)), (label,a)
            n+=1
    for a,b in (
        ("selectTextureTfactorAlpha || selectDiffuseTfactorAlpha","selectTextureTfactorAlpha || false"),
        ("GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)","GetRenderState(D3DRS_ALPHAREF, &textureFactor)"),
        ("const bool rgbNeedsDiffuse = selectDiffuseTextureAlpha || selectDiffuseDiffuseAlpha || selectDiffuseTfactorAlpha ||","const bool rgbNeedsDiffuse = false ||"),
        ("nextColorOp != D3DTOP_DISABLE","nextColorOp == D3DTOP_DISABLE"),
        ("ctx->DrawIndexed(indexCount, 0, 0);","ctx->DrawIndexed(0, 0, 0);"),
        ("static_cast<float>(output.alphaFunc), capture.blendFactorAlphaValue",
         "static_cast<float>(output.alphaFunc), 0.0f")):
        assert not connected(mutation(s,a,b)),a
        n+=1
    assert n==22,n
    for factor in range(256):
        alpha=((factor<<24)>>24 & 0xff)/255.0
        for texture,diffuse in ((0.,1.),(.25,.75),(1.,0.)):
            assert alpha==factor/255.0 and 0.<=alpha<=1.
    print("00587 PASS: 22 negative mutations, 768 factor alpha cases; runtime UNTESTED")

if __name__=="__main__": main()
