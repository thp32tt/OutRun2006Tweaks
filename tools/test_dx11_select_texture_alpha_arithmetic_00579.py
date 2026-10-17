#!/usr/bin/env python3
"""00579 live D3D9 stage0 texture RGB + saturating independent ADD/SUBTRACT alpha.
Static/destructive validation only; gamepad/Quest3/VDXR not tested.
"""
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
CASES = (
    ("selectTextureAddAlpha", "D3DTOP_ADD", "PSTextureSelectTextureAddAlpha", "selectTextureAddAlphaPs", "saturate(t.a + v.diffuse.a)"),
    ("selectTextureSubtractAlpha", "D3DTOP_SUBTRACT", "PSTextureSelectTextureSubtractAlpha", "selectTextureSubtractAlphaPs", "saturate(t.a - v.diffuse.a)"),
)
def connected(src):
    gate = src.split("bool supported_game_state(", 1)[-1].split("bool translate_vertices(", 1)[0]
    pipe = src.split("bool ensure_pipeline(", 1)[-1].split("bool supported_game_state(", 1)[0]
    draw = src.split("bool submit(", 1)[-1].split("void observe(", 1)[0]
    for flag, op, shader, owner, alpha in CASES:
        pred = f"const bool {flag} = op == D3DTOP_SELECTARG1 &&"
        if pred not in gate or not gate.split(pred,1)[1].lstrip().startswith(f"alphaOp == {op};"): return False
        if f"capture.{flag} = {flag};" not in gate or f"!{flag} &&" not in gate: return False
        if f"{flag} ||" not in gate.split("const bool alphaNeedsDiffuse =",1)[-1].split("if ((!modulate",1)[0]: return False
        if f"capture.{flag} ? s.{owner}.Get()" not in draw: return False
        for tok in (
            f"ComPtr<ID3D11PixelShader> {owner};", f"s.{owner} &&",
            f'!compile("{shader}", "ps_4_0",', f"s.{owner}.GetAddressOf()",
            f"nullptr, s.{owner}.GetAddressOf())) ||",
        ):
            if tok not in src: return False
        if src.count(f"s.{owner}.Reset();") != 2: return False
        block=src.split(f"float4 {shader}(VOut v) : SV_Target {{",1)[-1].split("\n}",1)[0]
        if f"float4 c = float4(t.rgb, {alpha});" not in block or "AlphaGate(c.a);" not in block: return False
    return all(t in gate for t in (
        "arg != D3DTA_TEXTURE", "alphaArg1 != D3DTA_TEXTURE",
        "(alphaNeedsDiffuse && !alphaArg2Diffuse)",
        "nextColorOp != D3DTOP_DISABLE", "coordIndex >= layout.texcoordCount",
    )) and all(t in draw for t in (
        "ctx->PSSetShaderResources(0, 1, &boundView)",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )) and "if (!diagnostic_enabled() || !game)" in src
def result_arg_fail_closed(source):
    gate = source.split("bool supported_game_state(", 1)[-1].split("bool translate_vertices(", 1)[0]
    return all(token in gate for token in (
        "DWORD op=0, arg=0, nextColorOp=0, resultArg=0;",
        "GetTextureStageState(0, D3DTSS_RESULTARG, &resultArg)",
        # Stage0 TEMP is never a valid native input even with opt-in stage1.
        # The stage1 result and stage2 stage are separately guarded.
        "resultArg != D3DTA_CURRENT",
        "stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
    )) and gate.index("resultArg != D3DTA_CURRENT") < gate.index("if (nextColorOp != D3DTOP_DISABLE)")

def run():
    src=SRC.read_text(encoding="utf8")
    assert connected(src), "00579 source->shader->draw/alpha gate disconnected"
    assert result_arg_fail_closed(src), "stage0 TEMP result must stay on DX9Ex"
    for old, replacement in (
        ("GetTextureStageState(0, D3DTSS_RESULTARG, &resultArg)",
         "GetTextureStageState(1, D3DTSS_RESULTARG, &resultArg)"),
        ("resultArg != D3DTA_CURRENT", "resultArg == D3DTA_CURRENT"),
        ("stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
         "stage1Result == D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE"),
        ("stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
         "stage1Result != D3DTA_CURRENT || stage2Op == D3DTOP_DISABLE"),
    ):
        broken = src.replace(old, replacement, 1)
        assert broken != src and not result_arg_fail_closed(broken), old
    negatives=0
    for flag,op,shader,owner,alpha in CASES:
        for old,bad in (
            (f"capture.{flag} = {flag};",f"capture.{flag} = false;"),
            (f"capture.{flag} ? s.{owner}.Get()",f"capture.{flag} ? nullptr"),
            (f"const bool {flag} = op == D3DTOP_SELECTARG1 &&",f"const bool {flag} = op == D3DTOP_MODULATE &&"),
            (f'!compile("{shader}", "ps_4_0",','!compile("PS", "ps_4_0",'),
            (f"s.{owner}.GetAddressOf()", "nullptr"),
            (f"float4 c = float4(t.rgb, {alpha});","float4 c = t;"),
            (f"alphaOp == {op};","alphaOp == D3DTOP_DISABLE;"),
        ):
            if old.startswith("alphaOp =="):
                idx=src.index(f"const bool {flag} = op == D3DTOP_SELECTARG1 &&")
                mutant=src[:idx]+src[idx:].replace(old,bad,1)
            else: mutant=src.replace(old,bad,1)
            assert mutant != src and not connected(mutant), (flag,old)
            negatives+=1
    for ta,da in ((0.8,0.6),(0.3,0.5),(0.2,0.9)):
        add=min(1.0,ta+da); sub=max(0.0,ta-da)
        assert 0 <= add <= 1 and 0 <= sub <= 1
        if ta==0.8: assert abs(add-1)<1e-8 and abs(sub-0.2)<1e-8
    for color,alpha,rgb,a1,a2,expected in (
        ("SELECTARG1","ADD","TEXTURE","TEXTURE","DIFFUSE",True),
        ("SELECTARG1","SUBTRACT","TEXTURE","TEXTURE","CURRENT",True),
        ("SELECTARG1","ADD","TEXTURE","DIFFUSE","DIFFUSE",False),
        ("SELECTARG1","SUBTRACT","TEXTURE","TEXTURE","TEXTURE",False),
        ("SELECTARG1","ADD","TEXTURE|COMPLEMENT","TEXTURE","DIFFUSE",False),
        ("SELECTARG1","ADD","TEXTURE","TEXTURE|ALPHAREPLICATE","DIFFUSE",False),
        ("SELECTARG2","ADD","TEXTURE","TEXTURE","DIFFUSE",False),
        ("SELECTARG1","MODULATE","TEXTURE","TEXTURE","DIFFUSE",False),
    ):
        actual=(color=="SELECTARG1" and alpha in ("ADD","SUBTRACT")
            and rgb=="TEXTURE" and a1=="TEXTURE" and a2 in ("DIFFUSE","CURRENT"))
        assert actual==expected,(color,alpha,rgb,a1,a2)
    assert negatives==14
    print("DX11 00579 independent ADD/SUBTRACT alpha live Draw static PASS: 14 alpha mutants + 2 RESULTARG negative mutations; HMD UNTESTED")
if __name__=="__main__": run()
