#!/usr/bin/env python3
"""00578 game stage0 SELECTARG1 texture RGB plus independent alpha; no runtime claims."""
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
CASES = (
    ("selectTextureDiffuseAlpha", "D3DTOP_SELECTARG2", "PSTextureSelectTextureDiffuseAlpha", "selectTextureDiffuseAlphaPs", "v.diffuse.a"),
    ("selectTextureModulateAlpha", "D3DTOP_MODULATE", "PSTextureSelectTextureModulateAlpha", "selectTextureModulateAlphaPs", "t.a * v.diffuse.a"),
)
def connected(s):
    gate = s.split("bool supported_game_state(", 1)[-1].split("bool translate_vertices(", 1)[0]
    pipe = s.split("bool ensure_pipeline(", 1)[-1].split("bool supported_game_state(", 1)[0]
    draw = s.split("bool submit(", 1)[-1].split("void observe(", 1)[0]
    for flag, op, shader, owner, alpha in CASES:
        pred = f"const bool {flag} = op == D3DTOP_SELECTARG1 &&"
        if pred not in gate or not gate.split(pred, 1)[1].lstrip().startswith(f"alphaOp == {op};"): return False
        if f"capture.{flag} = {flag};" not in gate or f"!{flag}" not in gate.split("if ((!modulate", 1)[-1].split("return false;", 1)[0]: return False
        if f"capture.{flag} ? s.{owner}.Get()" not in draw: return False
        if f"ComPtr<ID3D11PixelShader> {owner};" not in s: return False
        if f"s.{owner} &&" not in pipe or f"s.{owner}.Reset();" not in pipe: return False
        if f'!compile("{shader}", "ps_4_0",' not in pipe or f"s.{owner}.GetAddressOf())) ||" not in pipe: return False
        block = s.split(f"float4 {shader}(VOut v) : SV_Target {{", 1)[-1].split("\n}", 1)[0]
        if f"float4 c = float4(t.rgb, {alpha});" not in block or "AlphaGate(c.a);" not in block: return False
    return all(x in gate for x in ("selectTextureDiffuseAlpha || selectTextureModulateAlpha ||", "!selectTextureDiffuseAlpha && (!blendFactorDiffuseAlpha", "(alphaNeedsDiffuse && !alphaArg2Diffuse)", "arg != D3DTA_TEXTURE", "coordIndex >= layout.texcoordCount")) and all(x in draw for x in ("ctx->PSSetShaderResources(0, 1, &boundView)", "ctx->DrawIndexed(indexCount, 0, 0);", "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")) and "if (!diagnostic_enabled() || !game)" in s
def main():
    s = SRC.read_text(encoding="utf8")
    assert connected(s), "native texture independent alpha disconnected"
    edits = (
        ("capture.selectTextureDiffuseAlpha = selectTextureDiffuseAlpha;", "capture.selectTextureDiffuseAlpha = false;"),
        ("capture.selectTextureModulateAlpha = selectTextureModulateAlpha;", "capture.selectTextureModulateAlpha = false;"),
        ("capture.selectTextureDiffuseAlpha ? s.selectTextureDiffuseAlphaPs.Get()", "capture.selectTextureDiffuseAlpha ? nullptr"),
        ("capture.selectTextureModulateAlpha ? s.selectTextureModulateAlphaPs.Get()", "capture.selectTextureModulateAlpha ? nullptr"),
        ("float4 c = float4(t.rgb, v.diffuse.a);", "float4 c = float4(t.rgb, t.a);"),
        ("float4 c = float4(t.rgb, t.a * v.diffuse.a);", "float4 c = float4(t.rgb, t.a);"),
        ("s.selectTextureDiffuseAlphaPs.Reset();", ""),
        ("s.selectTextureModulateAlphaPs.Reset();", ""),
        ("!selectTextureDiffuseAlpha && (!blendFactorDiffuseAlpha", "!blendFactorDiffuseAlpha"),
        ("selectTextureDiffuseAlpha || selectTextureModulateAlpha ||", "selectTextureDiffuseAlpha ||"),
        ('!compile("PSTextureSelectTextureDiffuseAlpha", "ps_4_0",', '!compile("PS", "ps_4_0",'),
        ('!compile("PSTextureSelectTextureModulateAlpha", "ps_4_0",', '!compile("PS", "ps_4_0",'),
    )
    for old, bad in edits:
        assert old in s
        assert not connected(s.replace(old, bad, 1)), old
    samples = (
        ("SELECTARG1", "SELECTARG2", "TEXTURE", "IGNORED", "CURRENT", True),
        ("SELECTARG1", "SELECTARG2", "TEXTURE", "IGNORED", "DIFFUSE", True),
        ("SELECTARG1", "MODULATE", "TEXTURE", "TEXTURE", "DIFFUSE", True),
        ("SELECTARG1", "MODULATE", "TEXTURE", "TEXTURE", "CURRENT", True),
        ("SELECTARG2", "SELECTARG2", "TEXTURE", "IGNORED", "DIFFUSE", False),
        ("SELECTARG1", "MODULATE", "DIFFUSE", "TEXTURE", "DIFFUSE", False),
        ("SELECTARG1", "SELECTARG2", "TEXTURE", "IGNORED", "TEXTURE", False),
        ("SELECTARG1", "SELECTARG2", "TEXTURE", "IGNORED", "DIFFUSE|COMPLEMENT", False),
        ("SELECTARG1", "MODULATE", "TEXTURE", "DIFFUSE", "DIFFUSE", False),
        ("SELECTARG1", "MODULATE", "TEXTURE", "TEXTURE|ALPHAREPLICATE", "DIFFUSE", False),
        ("SELECTARG1", "MODULATE", "TEXTURE", "TEXTURE", "TEXTURE", False),
    )
    for cop, aop, rgb, a1, a2, accepted in samples:
        calc = cop == "SELECTARG1" and rgb == "TEXTURE" and a2 in ("DIFFUSE", "CURRENT") and (aop == "SELECTARG2" or (aop == "MODULATE" and a1 == "TEXTURE"))
        assert calc == accepted, (cop, aop, a1, a2)
    assert (0.25 * 0.72) == 0.18
    print("DX11 00578 texture RGB/alpha live Draw source and 12 destructive regressions PASS; runtime UNTESTED")
if __name__ == "__main__": main()
