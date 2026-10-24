#!/usr/bin/env python3
"""00580 SELECTARG2 diffuse RGB / independent texture + diffuse ADD/SUBTRACT alpha.
Only source and mathematical regression; Quest3/VDXR and gamepad untested.
"""
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
CASES = (
    ("selectDiffuseAddAlpha", "D3DTOP_ADD", "PSTextureSelectDiffuseAddAlpha",
     "selectDiffuseAddAlphaPs", "saturate(t.a + v.diffuse.a)"),
    ("selectDiffuseSubtractAlpha", "D3DTOP_SUBTRACT", "PSTextureSelectDiffuseSubtractAlpha",
     "selectDiffuseSubtractAlphaPs", "saturate(t.a - v.diffuse.a)"),
)
def connected(src):
    gate=src.split("bool supported_game_state(",1)[-1].split("bool translate_vertices(",1)[0]
    draw=src.split("bool submit(",1)[-1].split("void observe(",1)[0]
    ready=src.split("bool ensure_pipeline(",1)[-1].split("bool supported_game_state(",1)[0]
    for flag, op, shader, owner, math in CASES:
        predicate=f"const bool {flag} = op == D3DTOP_SELECTARG2 &&"
        if predicate not in gate or not gate.split(predicate,1)[1].lstrip().startswith(f"alphaOp == {op};"): return False
        if any(token not in gate for token in (f"capture.{flag} = {flag};",f"!{flag} &&",f"{flag} ||")): return False
        if f"capture.{flag} ? s.{owner}.Get()" not in draw: return False
        if any(token not in src for token in (
            f"ComPtr<ID3D11PixelShader> {owner};",
            f"s.{owner} &&",f'!compile("{shader}", "ps_4_0",',
            f"s.{owner}.GetAddressOf()",
        )): return False
        if src.count(f"s.{owner}.Reset();")!=2: return False
        block=src.split(f"float4 {shader}(VOut v) : SV_Target {{",1)[-1].split("\n}",1)[0]
        if f"float4 c = float4(v.diffuse.rgb, {math});" not in block or "AlphaGate(c.a);" not in block:return False
    return all(k in gate for k in (
        "arg != D3DTA_TEXTURE","(rgbNeedsDiffuse && !arg2Diffuse)",
        "(alphaNeedsDiffuse && !alphaArg2Diffuse)","alphaArg1 != D3DTA_TEXTURE",
        "resultArg != D3DTA_CURRENT",
        "stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
    )) and "if (!diagnostic_enabled() || !game)" in src and all(k in draw for k in (
        "ctx->PSSetShaderResources(0, 1, &boundView)",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    ))
def main():
    src=SRC.read_text(encoding="utf8")
    assert connected(src), "00580 native SELECTARG2 + arithmetic alpha disconnected"
    negatives=0
    for flag,op,shader,owner,math in CASES:
        pred=f"const bool {flag} = op == D3DTOP_SELECTARG2 &&"
        for old,bad in (
            (pred,f"const bool {flag} = op == D3DTOP_SELECTARG1 &&"),
            (f"capture.{flag} = {flag};",f"capture.{flag} = false;"),
            (f"capture.{flag} ? s.{owner}.Get()",f"capture.{flag} ? nullptr"),
            (f'!compile("{shader}", "ps_4_0",','!compile("PS", "ps_4_0",'),
            (f"s.{owner}.GetAddressOf()","nullptr"),
            (f"float4 c = float4(v.diffuse.rgb, {math});","float4 c = t;"),
            (f"alphaOp == {op};","alphaOp == D3DTOP_DISABLE;"),
        ):
            if old.startswith("alphaOp =="):
                idx=src.index(pred)
                mutant=src[:idx]+src[idx:].replace(old,bad,1)
            else: mutant=src.replace(old,bad,1)
            assert mutant != src and not connected(mutant),(flag,old)
            negatives+=1
    for old,bad in (
        ("resultArg != D3DTA_CURRENT","resultArg == D3DTA_CURRENT"),
        ("stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
         "stage1Result == D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE"),
        ("stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
         "stage1Result != D3DTA_CURRENT || stage2Op == D3DTOP_DISABLE"),
        ("(rgbNeedsDiffuse && !arg2Diffuse)","(rgbNeedsDiffuse && arg2Diffuse)"),
        ("(alphaNeedsDiffuse && !alphaArg2Diffuse)","(alphaNeedsDiffuse && alphaArg2Diffuse)"),
    ):
        mutant=src.replace(old,bad,1)
        assert mutant != src and not connected(mutant),old
        negatives+=1
    for t,v in ((0.,1.),(.9,.8),(.2,.6),(.9,.1)):
        add=min(1.,t+v); subtract=max(0.,t-v)
        assert 0<=add<=1 and 0<=subtract<=1
        if t==.9 and v==.8: assert add==1 and subtract>0
        if t==.2 and v==.6: assert subtract==0
    assert negatives==19
    print("00580 SELECTARG2 native alpha integration: 19 destructive mutations PASS; runtime UNTESTED")
if __name__=="__main__":main()
