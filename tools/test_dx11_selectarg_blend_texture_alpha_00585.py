#!/usr/bin/env python3
"""00585: game D3D9 SELECTARG1/2 RGB and independent texture-weighted alpha."""
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
CASES = (("Texture", "selectTextureBlendTextureAlpha", "SELECTARG1", "t.rgb"),
         ("Diffuse", "selectDiffuseBlendTextureAlpha", "SELECTARG2", "v.diffuse.rgb"))

def linked(s):
    if not all(x in s for x in ("bool ensure_pipeline(", "bool supported_game_state(", "bool submit(")):
        return False
    pipe = s.split("bool ensure_pipeline(",1)[1].split("bool supported_game_state(",1)[0]
    gate = s.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    draw = s.split("bool submit(",1)[1].split("void observe(",1)[0]
    if not all(x in gate for x in (
        "arg != D3DTA_TEXTURE", "alphaArg1 != D3DTA_TEXTURE",
        "(alphaNeedsDiffuse && !alphaArg2Diffuse)", "(rgbNeedsDiffuse && !arg2Diffuse)",
        "nextColorOp != D3DTOP_DISABLE", "resultArg != D3DTA_CURRENT")): return False
    if not all(x in draw for x in ("ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
            "ctx->PSSetShaderResources(0, 1, &boundView)")): return False
    if 'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"' not in s: return False
    for label, flag, op, rgb in CASES:
        entry = "PSTextureSelect" + label + "BlendTextureAlpha"
        prefix = "float4 " + entry + "(VOut v) : SV_Target {"
        if prefix not in s: return False
        shader = s.split(prefix,1)[1].split("}",1)[0]
        if ("float4 c = float4(" + rgb + ", lerp(v.diffuse.a, t.a, t.a));" not in shader
                or "AlphaGate(c.a)" not in shader): return False
        if not all(x in gate for x in (
                "const bool " + flag + " = op == D3DTOP_" + op + " &&",
                "alphaOp == D3DTOP_BLENDTEXTUREALPHA;",
                "capture." + flag + " = " + flag + ";",
                "!" + flag + " &&")): return False
        if flag not in gate.split("const bool alphaNeedsDiffuse =",1)[1].split("if ((",1)[0]: return False
        if label == "Diffuse" and flag not in gate.split("const bool rgbNeedsDiffuse =",1)[1].split("const bool alphaNeedsDiffuse =",1)[0]: return False
        if not all(x in pipe for x in ("s."+flag+"Ps &&", '!compile("'+entry+'", "ps_4_0",',
                "s."+flag+"Ps.GetAddressOf()")): return False
        if "capture."+flag+" ? s."+flag+"Ps.Get()" not in draw: return False
        if "ComPtr<ID3D11PixelShader> "+flag+"Ps;" not in s: return False
        if s.count("s."+flag+"Ps.Reset();") != 2: return False
    return True

def mutate(s,a,b):
    assert s.count(a)==1, (a,s.count(a))
    return s.replace(a,b,1)

def main():
    s = P.read_text(encoding="utf-8")
    assert linked(s), "stage capture/PS/Draw/DrawIndexed disconnected"
    n=0
    for label,flag,op,rgb in CASES:
        entry="PSTextureSelect"+label+"BlendTextureAlpha"
        for a,b in (
            ("const bool "+flag+" = op == D3DTOP_"+op+" &&","const bool "+flag+" = op == D3DTOP_DISABLE &&"),
            ("capture."+flag+" = "+flag+";","capture."+flag+" = false;"),
            ("!"+flag+" &&","!"+flag+" ||"),
            ("capture."+flag+" ? s."+flag+"Ps.Get()","capture."+flag+" ? nullptr"),
            ("s."+flag+"Ps.GetAddressOf()","nullptr"),
            ('!compile("'+entry+'", "ps_4_0",','!compile("bad", "ps_4_0",'),
            ("float4 c = float4("+rgb+", lerp(v.diffuse.a, t.a, t.a));",
             "float4 c = float4("+rgb+", t.a);"),
            ("ComPtr<ID3D11PixelShader> "+flag+"Ps;","ComPtr<ID3D11PixelShader> dummy;")):
            assert not linked(mutate(s,a,b)),(label,a)
            n+=1
    for a,b in (
        ("alphaArg1 != D3DTA_TEXTURE","alphaArg1 == D3DTA_TEXTURE"),
        ("(alphaNeedsDiffuse && !alphaArg2Diffuse)","(alphaNeedsDiffuse && alphaArg2Diffuse)"),
        ("nextColorOp != D3DTOP_DISABLE","nextColorOp == D3DTOP_DISABLE"),
        ("ctx->DrawIndexed(indexCount, 0, 0);","ctx->DrawIndexed(0, 0, 0);")):
        assert not linked(mutate(s,a,b)),a
        n+=1
    assert n==20,n
    for t in (0.,.1,.25,.5,.75,.9,1.):
        for d in (0.,.3,.6,1.):
            alpha=d+t*(t-d)
            assert 0<=alpha<=1 and abs(alpha-(t*t+d*(1-t)))<1e-12
    print("00585 PASS: 20 destructive mutations and 28 alpha cases, HMD UNTESTED")

if __name__=="__main__": main()
