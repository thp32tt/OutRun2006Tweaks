#!/usr/bin/env python3
"""00582 game-authored D3D9 stage0 ADDSMOOTH alpha -> native D3D11 draw."""
from pathlib import Path
S = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
CASES = (
    ("selectTextureAddSmoothAlpha", "D3DTOP_SELECTARG1", "PSTextureSelectTextureAddSmoothAlpha", "t.rgb"),
    ("selectDiffuseAddSmoothAlpha", "D3DTOP_SELECTARG2", "PSTextureSelectDiffuseAddSmoothAlpha", "v.diffuse.rgb"),
)
A = "saturate(t.a + v.diffuse.a * (1.0f - t.a))"
def linked(s):
    if "bool supported_game_state(" not in s or "bool submit(" not in s: return False
    g = s.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    p = s.split("bool ensure_pipeline(",1)[1].split("bool supported_game_state(",1)[0]
    d = s.split("bool submit(",1)[1].split("void observe(",1)[0]
    for name, op, shader, rgb in CASES:
        owner = name + "Ps"
        key = "const bool " + name + " = op == " + op + " &&"
        if key not in g or not g.split(key,1)[1].lstrip().startswith("alphaOp == D3DTOP_ADDSMOOTH;"): return False
        if any(x not in g for x in ("capture." + name + " = " + name + ";", "!" + name + " &&", name + " ||",
                                     "alphaArg1 != D3DTA_TEXTURE", "arg != D3DTA_TEXTURE",
                                     "(alphaNeedsDiffuse && !alphaArg2Diffuse)",
                                     "resultArg != D3DTA_CURRENT")): return False
        if name.startswith("selectDiffuse") and "(rgbNeedsDiffuse && !arg2Diffuse)" not in g: return False
        if any(x not in p for x in ("s." + owner + " &&", '!compile("' + shader + '", "ps_4_0",',
                                     "s." + owner + ".GetAddressOf()")): return False
        if "capture." + name + " ? s." + owner + ".Get()" not in d: return False
        if "ComPtr<ID3D11PixelShader> " + owner + ";" not in s or s.count("s." + owner + ".Reset();") != 2: return False
        if "float4 " + shader + "(VOut v) : SV_Target {" not in s: return False
        if "float4 c = float4(" + rgb + ", " + A + ");" not in s: return False
    return ("ctx->DrawIndexed(indexCount, 0, 0);" in d and
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in d and
            "ctx->PSSetShaderResources(0, 1, &boundView)" in d and
            'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"' in s and
            "if (!diagnostic_enabled() || !game)" in s and
            "static const std::string shaderSource = std::string(kShader) + kScaledAlphaShader;" in s)
def main():
    s = S.read_text(encoding="utf-8")
    assert linked(s), "00582 game shader/Draw path disconnected"
    n = 0
    for name, op, shader, rgb in CASES:
        owner = name + "Ps"
        key = "const bool " + name + " = op == " + op + " &&"
        for old, bad in (
            (key, key.replace(op, "D3DTOP_DISABLE")),
            ("alphaOp == D3DTOP_ADDSMOOTH;", "alphaOp == D3DTOP_DISABLE;"),
            ("capture." + name + " = " + name + ";", "capture." + name + " = false;"),
            ("!" + name + " &&", "!" + name + " ||"),
            ("capture." + name + " ? s." + owner + ".Get()", "capture." + name + " ? nullptr"),
            ("s." + owner + ".GetAddressOf()", "nullptr"),
            ('!compile("' + shader + '", "ps_4_0",', '!compile("PS", "ps_4_0",'),
            ("float4 c = float4(" + rgb + ", " + A + ");", "float4 c = t;"),
        ):
            if old == "alphaOp == D3DTOP_ADDSMOOTH;":
                pos = s.index(key)
                mutant = s[:pos] + s[pos:].replace(old,bad,1)
            else: mutant = s.replace(old,bad,1)
            assert mutant != s and not linked(mutant), (name,old)
            n += 1
    for old,bad in (
        ("(alphaNeedsDiffuse && !alphaArg2Diffuse)", "(alphaNeedsDiffuse && alphaArg2Diffuse)"),
        ("alphaArg1 != D3DTA_TEXTURE", "alphaArg1 == D3DTA_TEXTURE"),
        ("resultArg != D3DTA_CURRENT", "resultArg == D3DTA_CURRENT"),
        ("static const std::string shaderSource = std::string(kShader) + kScaledAlphaShader;",
         "static const std::string shaderSource = std::string(kShader);"),
    ):
        mutant = s.replace(old,bad,1)
        assert mutant != s and not linked(mutant), old
        n += 1
    assert n == 20, n
    for t,v in ((0.,0.),(0.,1.),(.2,.8),(.6,.25),(1.,.7)):
        alpha = min(1.,max(0.,t+v*(1.-t)))
        assert abs(alpha - (t+(1.-t)*v)) < 1e-8 and t <= alpha <= 1.
    print("00582: 20 destructive mutations and 5 alpha cases PASS; HMD UNTESTED")
if __name__ == "__main__": main()
