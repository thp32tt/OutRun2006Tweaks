#!/usr/bin/env python3
"""DX11 00584 D3D9 RGB SELECTARG with independent texture-factor alpha."""
from pathlib import Path
import re

P = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
V = (("selectTextureFactorAlpha", "SELECTARG1", "Texture", "t.rgb"),
     ("selectDiffuseFactorAlpha", "SELECTARG2", "Diffuse", "v.diffuse.rgb"))

def linked(s):
    if "bool supported_game_state(" not in s or "bool submit(" not in s: return False
    gate = s.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    pipe = s.split("bool ensure_pipeline(",1)[1].split("bool supported_game_state(",1)[0]
    draw = s.split("bool submit(",1)[1].split("void observe(",1)[0]
    for tok in ("arg != D3DTA_TEXTURE", "alphaArg1 != D3DTA_TEXTURE",
                "(alphaNeedsDiffuse && !alphaArg2Diffuse)", "(rgbNeedsDiffuse && !arg2Diffuse)",
                "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)",
                "((textureFactor >> 24u) & 0xffu) / 255.0f",
                "nextColorOp != D3DTOP_DISABLE", "resultArg != D3DTA_CURRENT"):
        if tok not in gate: return False
    for tok in ("ctx->DrawIndexed(indexCount, 0, 0);",
                "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
                "ctx->PSSetShaderResources(0, 1, &boundView)"):
        if tok not in draw: return False
    if 'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"' not in s: return False
    for flag,op,label,rgb in V:
        shader="PSTextureSelect"+label+"FactorAlpha"
        ps="float4 "+shader+"(VOut v) : SV_Target {"
        c="float4 c = float4("+rgb+", lerp(v.diffuse.a, t.a, alphaParams.w));"
        if ps not in s or c not in s.split(ps,1)[1].split("}",1)[0]: return False
        for tok in ("const bool "+flag+" = op == D3DTOP_"+op+" &&",
                    "alphaOp == D3DTOP_BLENDFACTORALPHA;",
                    "capture."+flag+" = "+flag+";", "!"+flag+" &&",
                    "bool "+flag+" = false;", "ComPtr<ID3D11PixelShader> "+flag+"Ps;"):
            if tok not in s: return False
        if flag not in gate.split("const bool alphaNeedsDiffuse =",1)[1].split("if ((",1)[0]: return False
        if label=="Diffuse" and flag not in gate.split("const bool rgbNeedsDiffuse =",1)[1].split("const bool alphaNeedsDiffuse =",1)[0]: return False
        for tok in ("s."+flag+"Ps &&", '!compile("'+shader+'", "ps_4_0",',
                    "s."+flag+"Ps.GetAddressOf()"):
            if tok not in pipe: return False
        if "capture."+flag+" ? s."+flag+"Ps.Get()" not in draw: return False
        if s.count("s."+flag+"Ps.Reset();") != 2: return False
    # Additional native stage0 alpha operations also need TFACTOR. Verify
    # both historical SELECTARG routes remain inside the *same* live read
    # guard, without assuming they are the last members of its OR chain.
    factor_guard = gate.split("DWORD textureFactor = 0;", 1)[1].split(
        "FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor))", 1)[0]
    if "if ((" not in factor_guard or not re.search(
            r"\bselectTextureFactorAlpha\s*\|\|\s*selectDiffuseFactorAlpha\s*(?:\|\||\))",
            factor_guard):
        return False
    # The factor-alpha predicates must be defined before the read that uses
    # them. Static graph checks alone previously missed Win32 error C2065.
    factor_read = gate.find("DWORD textureFactor = 0;")
    if factor_read < 0: return False
    for flag, _, _, _ in V:
        decl = gate.find("const bool " + flag + " =")
        if decl < 0 or decl > factor_read: return False
    return True

def mutate(s,a,b):
    occurrences = s.count(a)
    # 00635 added a second independently guarded TFACTOR read for
    # complemented PM alpha. Mutate both sites to ensure that no valid
    # factor source remains, while leaving other mutations uniquely scoped.
    if a == "GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)":
        assert occurrences >= 1, (a, occurrences)
        return s.replace(a, b)
    assert occurrences == 1, (a, occurrences)
    return s.replace(a, b, 1)

def main():
    s=P.read_text(encoding="utf-8")
    assert linked(s),"D3D9 RGB/factor -> HLSL -> native Draw is disconnected"
    count=0
    for flag,op,label,rgb in V:
        shader="PSTextureSelect"+label+"FactorAlpha"
        for a,b in (
            ("const bool "+flag+" = op == D3DTOP_"+op+" &&", "const bool "+flag+" = op == D3DTOP_DISABLE &&"),
            ("capture."+flag+" = "+flag+";", "capture."+flag+" = false;"),
            ("!"+flag+" &&", "!"+flag+" ||"),
            ("capture."+flag+" ? s."+flag+"Ps.Get()", "capture."+flag+" ? nullptr"),
            ("s."+flag+"Ps.GetAddressOf()", "nullptr"),
            ('!compile("'+shader+'", "ps_4_0",', '!compile("Broken", "ps_4_0",'),
            ("float4 c = float4("+rgb+", lerp(v.diffuse.a, t.a, alphaParams.w));",
             "float4 c = float4("+rgb+", t.a);"),
            ("ComPtr<ID3D11PixelShader> "+flag+"Ps;", "ComPtr<ID3D11PixelShader> broken;")):
            assert not linked(mutate(s,a,b)),(flag,a)
            count+=1
    for a,b in (
        ("alphaArg1 != D3DTA_TEXTURE", "alphaArg1 == D3DTA_TEXTURE"),
        ("(alphaNeedsDiffuse && !alphaArg2Diffuse)", "(alphaNeedsDiffuse && alphaArg2Diffuse)"),
        ("GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)", "GetRenderState(D3DRS_ALPHAREF, &textureFactor)"),
        ("((textureFactor >> 24u) & 0xffu) / 255.0f", "((textureFactor >> 16u) & 0xffu) / 255.0f")):
        assert not linked(mutate(s,a,b)),a
        count+=1
    # Win32 declaration-order regression: simulate moving a live predicate
    # after its first use without changing its shader or D3D9 semantics.
    factor_guard_end = ("            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))\n"
                        "            return false;\n")
    for flag, op, _, _ in V:
        declaration = ("        const bool " + flag + " = op == D3DTOP_" + op +
                       " &&\n                                      alphaOp == D3DTOP_BLENDFACTORALPHA;\n")
        assert s.count(declaration) == 1 and s.count(factor_guard_end) >= 1
        mutant = s.replace(declaration, "", 1).replace(
            factor_guard_end, factor_guard_end + declaration, 1)
        assert not linked(mutant), flag + " declaration-before-use"
        count += 1
    # Both RGB select modes are mutually exclusive; replacing OR with AND
    # would strand both previously supported factor-alpha draw paths.
    assert not linked(mutate(s,
        "selectTextureFactorAlpha || selectDiffuseFactorAlpha ||\n              blendTextureAlphaPMFactorArg2Alpha) &&",
        "selectTextureFactorAlpha && selectDiffuseFactorAlpha ||\n              blendTextureAlphaPMFactorArg2Alpha) &&")), "factor guard OR broken"
    count += 1
    assert count==23,count
    for byte in (0,1,64,128,192,255):
        f=byte/255.0
        for t,d in ((0.0,1.0),(1.0,0.0),(.75,.25),(.2,.8)):
            a=d+(t-d)*f
            assert 0.0<=a<=1.0 and abs(a-((1.0-f)*d+f*t))<1e-12
    print("00584 PASS: 23 destructive source mutations, 24 alpha cases, live Draw path; HMD UNTESTED")

if __name__=="__main__": main()
