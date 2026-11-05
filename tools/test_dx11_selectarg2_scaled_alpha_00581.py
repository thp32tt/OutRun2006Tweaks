#!/usr/bin/env python3
"""00581 stage0 D3D9 SELECTARG2 RGB, independent MODULATE2X/4X alpha.
Static source and negative mutation checks; HMD/gamepad remain untested.
"""
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
CASES = (
    ("selectDiffuseModulate2XAlpha", "D3DTOP_MODULATE2X", "PSTextureSelectDiffuseModulate2XAlpha", "2.0f"),
    ("selectDiffuseModulate4XAlpha", "D3DTOP_MODULATE4X", "PSTextureSelectDiffuseModulate4XAlpha", "4.0f"),
)
def connected(src):
    gate = src.split("bool supported_game_state(", 1)[-1].split("bool translate_vertices(", 1)[0]
    ready = src.split("bool ensure_pipeline(", 1)[-1].split("bool supported_game_state(", 1)[0]
    draw = src.split("bool submit(", 1)[-1].split("void observe(", 1)[0]
    for flag, op, shader, scale in CASES:
        owner = flag + "Ps"
        pred = f"const bool {flag} = op == D3DTOP_SELECTARG2 &&"
        if pred not in gate or not gate.split(pred, 1)[1].lstrip().startswith(f"alphaOp == {op};"): return False
        if any(x not in gate for x in (
            f"capture.{flag} = {flag};", f"!{flag} &&", f"{flag} ||",
            "(rgbNeedsDiffuse && !arg2Diffuse)", "(alphaNeedsDiffuse && !alphaArg2Diffuse)",
            "alphaArg1 != D3DTA_TEXTURE", "resultArg != D3DTA_CURRENT",
        )): return False
        if f"capture.{flag} ? s.{owner}.Get()" not in draw: return False
        if any(x not in ready for x in (
            f"s.{owner} &&", f'!compile("{shader}", "ps_4_0",', f"s.{owner}.GetAddressOf()",
        )): return False
        if f"ComPtr<ID3D11PixelShader> {owner};" not in src or src.count(f"s.{owner}.Reset();") != 2:
            return False
        code = src.split(f"float4 {shader}(VOut v) : SV_Target {{", 1)[-1].split("\n}", 1)[0]
        if f"float4 c = float4(v.diffuse.rgb, saturate({scale} * t.a * v.diffuse.a));" not in code or "AlphaGate(c.a); return c;" not in code: return False
    return ("constexpr char kScaledAlphaShader[] = R\"(" in src and
            "static const std::string shaderSource = std::string(kShader) + kScaledAlphaShader;" in src and
            "static const std::string stage1ShaderSource = shaderSource + kStage1FactorShader;" in src and
            "D3DCompile(stage1ShaderSource.data(), stage1ShaderSource.size()," in src and
            "if (!diagnostic_enabled() || !game)" in src and all(x in draw for x in (
        "ctx->PSSetShaderResources(0, 1, &boundView)",
        "ctx->DrawIndexed(indexCount, 0, 0);", "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )))
def main():
    src = SRC.read_text(encoding="utf-8")
    assert connected(src), "00581 game native SELECTARG2 scaled-alpha disconnected"
    negatives = 0
    for flag, op, shader, scale in CASES:
        owner = flag + "Ps"
        pred = f"const bool {flag} = op == D3DTOP_SELECTARG2 &&"
        changes = (
            (pred, f"const bool {flag} = op == D3DTOP_SELECTARG1 &&"),
            (f"alphaOp == {op};", "alphaOp == D3DTOP_DISABLE;"),
            (f"capture.{flag} = {flag};", f"capture.{flag} = false;"),
            (f"!{flag} &&", f"#{flag} &&"),
            (f"capture.{flag} ? s.{owner}.Get()", f"capture.{flag} ? nullptr"),
            (f"s.{owner}.GetAddressOf()", "nullptr"),
            (f'!compile("{shader}", "ps_4_0",', '!compile("PS", "ps_4_0",'),
            (f"float4 c = float4(v.diffuse.rgb, saturate({scale} * t.a * v.diffuse.a));", "float4 c = t;"),
        )
        for old, bad in changes:
            mutant = src[:src.index(pred)] + src[src.index(pred):].replace(old,bad,1) if old.startswith("alphaOp ==") else src.replace(old,bad,1)
            assert mutant != src and not connected(mutant), (flag, old)
            negatives += 1
    for old, bad in (
        ("(rgbNeedsDiffuse && !arg2Diffuse)", "(rgbNeedsDiffuse && arg2Diffuse)"),
        ("(alphaNeedsDiffuse && !alphaArg2Diffuse)", "(alphaNeedsDiffuse && alphaArg2Diffuse)"),
        ("resultArg != D3DTA_CURRENT", "resultArg == D3DTA_CURRENT"),
    ):
        mutant = src.replace(old,bad,1)
        assert mutant != src and not connected(mutant), old
        negatives += 1
    for tex, diffuse in ((0.,1.),(.1,.9),(.4,.5),(.9,.8),(1.,1.)):
        for scale in (2.,4.):
            a = min(1., scale*tex*diffuse)
            assert 0. <= a <= 1.
            if tex==.9 and diffuse==.8: assert a==1.
            if tex==.1 and diffuse==.9: assert a<1.
    for old, bad in (
        ("static const std::string shaderSource = std::string(kShader) + kScaledAlphaShader;",
         "static const std::string shaderSource = std::string(kShader);"),
        ("D3DCompile(stage1ShaderSource.data(), stage1ShaderSource.size(),",
         "D3DCompile(kShader, sizeof(kShader) - 1,"),
    ):
        mutant = src.replace(old, bad, 1)
        assert mutant != src and not connected(mutant), old
        negatives += 1
    assert negatives == 21, negatives
    print("00581 SELECTARG2 native scaled alpha: 21 destructive mutations PASS; HMD UNTESTED")
if __name__ == "__main__": main()
