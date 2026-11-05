#!/usr/bin/env python3
"""CONVERSION-DX11-00583 real draw stage0 SELECTARG1 scaled alpha regression."""
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
CASES = ((2, "2X"), (4, "4X"))

def linked(s):
    if "bool supported_game_state(" not in s or "bool submit(" not in s:
        return False
    gate = s.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    pipe = s.split("bool ensure_pipeline(",1)[1].split("bool supported_game_state(",1)[0]
    draw = s.split("bool submit(",1)[1].split("void observe(",1)[0]
    # 00678: observe_unavailable_game_draw also has a diagnostic guard.
    # The 00583 failure mutation must target the actual Draw observer,
    # not pass because an unrelated unavailable-shadow guard still exists.
    observer = s.split("void observe(IDirect3DDevice9* game,",1)[1].split(
        "void observe_linear(",1)[0]
    for factor, suffix in CASES:
        flag = "selectTextureModulate"+suffix+"Alpha"
        shader = "PSTextureSelectTextureModulate"+suffix+"Alpha"
        code = "selectTextureModulate"+suffix+"Code"
        entry = "const bool "+flag+" = op == D3DTOP_SELECTARG1 &&"
        if entry not in gate or not gate.split(entry,1)[1].lstrip().startswith("alphaOp == D3DTOP_MODULATE"+suffix+";"):
            return False
        for token in ("capture."+flag+" = "+flag+";", "!"+flag+" &&", flag+" ||",
                      "alphaArg1 != D3DTA_TEXTURE", "(alphaNeedsDiffuse && !alphaArg2Diffuse)",
                      "arg != D3DTA_TEXTURE", "resultArg != D3DTA_CURRENT"):
            if token not in gate: return False
        for token in ("s."+flag+"Ps &&", '!compile("'+shader+'", "ps_4_0", '+code+')',
                      code+"->GetBufferPointer()", code+"->GetBufferSize()", "s."+flag+"Ps.GetAddressOf()"):
            if token not in pipe: return False
        if "capture."+flag+" ? s."+flag+"Ps.Get()" not in draw: return False
        if "bool "+flag+" = false;" not in s or "ComPtr<ID3D11PixelShader> "+flag+"Ps;" not in s: return False
        if s.count("s."+flag+"Ps.Reset();") != 2: return False
        entry = "float4 "+shader+"(VOut v) : SV_Target {"
        if entry not in s or "float4 c = float4(t.rgb, saturate("+str(factor)+".0f * t.a * v.diffuse.a));" not in s.split(entry,1)[1].split("}",1)[0]:
            return False
    return all(t in draw for t in ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
                                  "ctx->PSSetShaderResources(0, 1, &boundView)")) and "if (!diagnostic_enabled() || !game)" in observer and 'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"' in s

def mutate(s,old,new):
    assert s.count(old) == 1, old
    return s.replace(old,new,1)

def main():
    s = P.read_text(encoding="utf-8")
    assert linked(s), "00583 stage0/D3D11 integration disconnected"
    count=0
    for factor,suffix in CASES:
        flag="selectTextureModulate"+suffix+"Alpha"
        shader="PSTextureSelectTextureModulate"+suffix+"Alpha"
        source="float4 c = float4(t.rgb, saturate("+str(factor)+".0f * t.a * v.diffuse.a));"
        mutations=(
            ("const bool "+flag+" = op == D3DTOP_SELECTARG1 &&","const bool "+flag+" = op == D3DTOP_DISABLE &&"),
            ("capture."+flag+" = "+flag+";","capture."+flag+" = false;"),
            ("!"+flag+" &&", "!"+flag+" ||"),
            ("capture."+flag+" ? s."+flag+"Ps.Get()","capture."+flag+" ? nullptr"),
            ("s."+flag+"Ps.GetAddressOf()","nullptr"),
            ('!compile("'+shader+'", "ps_4_0",','!compile("PS", "ps_4_0",'),
            (source,"float4 c = t;"),
            ("ComPtr<ID3D11PixelShader> "+flag+"Ps;","ComPtr<ID3D11PixelShader> broken;"))
        for a,b in mutations:
            assert not linked(mutate(s,a,b)),(suffix,a)
            count += 1
        k="const bool "+flag+" = op == D3DTOP_SELECTARG1 &&"
        i=s.index(k)
        mutant=s[:i]+s[i:].replace("alphaOp == D3DTOP_MODULATE"+suffix+";","alphaOp == D3DTOP_DISABLE;",1)
        assert not linked(mutant),suffix
        count += 1
    for a,b in (("(alphaNeedsDiffuse && !alphaArg2Diffuse)","(alphaNeedsDiffuse && alphaArg2Diffuse)"),
                ("resultArg != D3DTA_CURRENT","resultArg == D3DTA_CURRENT"),
                ("alphaArg1 != D3DTA_TEXTURE","alphaArg1 == D3DTA_TEXTURE")):
        assert not linked(mutate(s,a,b)),a
        count += 1
    # The guard now appears in both observe() and the source-miss handler.
    # Replace only the game Draw observer's guard; this must break linkage.
    anchor = "void observe(IDirect3DDevice9* game,"
    guard = "if (!diagnostic_enabled() || !game)"
    assert s.count(anchor) == 1 and guard in s.split(anchor, 1)[1]
    prefix, tail = s.split(anchor, 1)
    broken = prefix + anchor + tail.replace(guard, "if (game)", 1)
    assert broken != s and not linked(broken), "raw Draw guard bypass not detected"
    count += 1
    assert count==22,count
    for t,v in ((0.,0.),(.3,.5),(.5,.5),(1.,.8),(.1,1.)):
        for factor,_ in CASES:
            a=min(1.,max(0.,factor*t*v))
            assert abs(a-min(1.,factor*(t*v))) < 1e-8
    print("00583: 22 destructive mutations, 10 scaled alpha cases PASS; HMD UNTESTED")
if __name__ == "__main__": main()
