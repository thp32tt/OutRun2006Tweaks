#!/usr/bin/env python3
"""00577: game TEX1 SELECTARG2 RGB with independent alpha, source-only proof.

CI/static results do not imply tested game, gamepad, Quest 3, or VDXR output.
"""
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
CASES = (
    ("selectDiffuseTextureAlpha", "D3DTOP_SELECTARG1", "PSTextureSelectDiffuseTextureAlpha", "selectDiffuseTextureAlphaPs", "t.a"),
    ("selectDiffuseDiffuseAlpha", "D3DTOP_SELECTARG2", "PS", "ps", "v.diffuse.a"),
    ("selectDiffuseModulateAlpha", "D3DTOP_MODULATE", "PSTextureSelectDiffuseModulateAlpha", "selectDiffuseModulateAlphaPs", "t.a * v.diffuse.a"),
)

def connected(src, case):
    flag, op, shader, owner, alpha = case
    gate = src.split("bool supported_game_state(", 1)[-1].split("bool translate_vertices(", 1)[0]
    pipe = src.split("bool ensure_pipeline(", 1)[-1].split("bool supported_game_state(", 1)[0]
    draw = src.split("bool submit(", 1)[-1].split("void observe(", 1)[0]
    predicate = f"const bool {flag} = op == D3DTOP_SELECTARG2 &&"
    if predicate not in gate or not gate.split(predicate, 1)[1].lstrip().startswith(f"alphaOp == {op};"):
        return False
    if f"capture.{flag} = {flag};" not in gate or f"!{flag}" not in gate.split("if ((!modulate && !selectTexture", 1)[-1].split("return false;", 1)[0]:
        return False
    if f"{flag} ||" not in gate.split("const bool rgbNeedsDiffuse =", 1)[-1].split("const bool alphaNeedsDiffuse =", 1)[0]:
        return False
    if flag != "selectDiffuseTextureAlpha" and f"{flag} ||" not in gate.split("const bool alphaNeedsDiffuse =", 1)[-1].split("if ((!modulate", 1)[0]:
        return False
    if "arg != D3DTA_TEXTURE" not in gate or "alphaArg1 != D3DTA_TEXTURE" not in gate:
        return False
    if f"capture.{flag} ? s.{owner}.Get()" not in draw or "ctx->DrawIndexed(indexCount, 0, 0);" not in draw or "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" not in draw:
        return False
    if owner != "ps":
        if f"ComPtr<ID3D11PixelShader> {owner};" not in src or f'!compile("{shader}", "ps_4_0",' not in pipe or f"nullptr, s.{owner}.GetAddressOf())) ||" not in pipe:
            return False
        body = src.split(f"float4 {shader}(VOut v) : SV_Target {{", 1)[-1].split("\n}", 1)[0]
        if f"float4 c = float4(v.diffuse.rgb, {alpha});" not in body or "AlphaGate(c.a);" not in body:
            return False
    elif "float4 PS(VOut v) : SV_Target { float4 c = v.diffuse; AlphaGate(c.a); return c; }" not in src:
        return False
    return True

def run():
    src = SRC.read_text(encoding="utf-8")
    for case in CASES:
        flag, op, shader, owner, alpha = case
        assert connected(src, case), flag
        for old, bad in (
            (f"capture.{flag} = {flag};", f"capture.{flag} = false;"),
            (f"capture.{flag} ? s.{owner}.Get()", f"capture.{flag} ? nullptr"),
            (f"const bool {flag} = op == D3DTOP_SELECTARG2 &&", f"const bool {flag} = op == D3DTOP_MODULATE &&"),
        ):
            mutant = src.replace(old, bad, 1)
            assert mutant != src and not connected(mutant, case), (flag, old)
        if shader != "PS":
            old = f"float4 c = float4(v.diffuse.rgb, {alpha});"
            mutant = src.replace(old, "float4 c = float4(v.diffuse.rgb, 1.0f);", 1)
            assert mutant != src and not connected(mutant, case), flag
    # Fixed-function color is DIFFUSE; alpha is independently selected.
    rgb, t_alpha, d_alpha = (0.15, 0.6, 0.95), 0.25, 0.8
    values = (t_alpha, d_alpha, t_alpha * d_alpha)
    assert values == (0.25, 0.8, 0.2)
    assert all(0 <= x <= 1 and rgb == (0.15, 0.6, 0.95) for x in values)
    # Invalid ops, sources and operand modifiers must remain fail-closed.
    examples = (
        ("SELECTARG2", "SELECTARG1", "DIFFUSE", "TEXTURE", "DIFFUSE", True),
        ("SELECTARG2", "SELECTARG2", "CURRENT", "UNUSED", "CURRENT", True),
        ("SELECTARG2", "MODULATE", "DIFFUSE", "TEXTURE", "DIFFUSE", True),
        ("SELECTARG1", "SELECTARG1", "DIFFUSE", "TEXTURE", "DIFFUSE", False),
        ("SELECTARG2", "ADD", "DIFFUSE", "TEXTURE", "DIFFUSE", False),
        ("SELECTARG2", "MODULATE", "TEXTURE", "TEXTURE", "DIFFUSE", False),
        ("SELECTARG2", "MODULATE", "CURRENT", "TEXTURE|COMPLEMENT", "DIFFUSE", False),
        ("SELECTARG2", "MODULATE", "DIFFUSE", "TEXTURE", "TEXTURE", False),
    )
    for cop, aop, rgb_src, a1, a2, accepted in examples:
        valid = (cop == "SELECTARG2" and rgb_src in ("DIFFUSE", "CURRENT") and
                 ((aop == "SELECTARG1" and a1 == "TEXTURE") or
                  (aop == "SELECTARG2" and a2 in ("DIFFUSE", "CURRENT")) or
                  (aop == "MODULATE" and a1 == "TEXTURE" and a2 in ("DIFFUSE", "CURRENT"))))
        assert valid == accepted, (cop, aop)
    print("DX11 00577 textured diffuse RGB/independent alpha source regressions PASS (runtime UNTESTED)")

if __name__ == "__main__":
    run()
