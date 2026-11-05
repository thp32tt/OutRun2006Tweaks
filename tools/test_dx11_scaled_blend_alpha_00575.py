#!/usr/bin/env python3
"""00575 real D3D9 texture/diffuse RGB blend + independent alpha 2x/4x source tests.

Static graph/model evidence only. Never claim live GPU/Quest3/gamepad PASS.
"""
from pathlib import Path

BRIDGE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
VARIANTS = (
    ("Texture", "2X", "2.0f", "t.a", "D3DTOP_BLENDTEXTUREALPHA"),
    ("Diffuse", "2X", "2.0f", "v.diffuse.a", "D3DTOP_BLENDDIFFUSEALPHA"),
    ("Texture", "4X", "4.0f", "t.a", "D3DTOP_BLENDTEXTUREALPHA"),
    ("Diffuse", "4X", "4.0f", "v.diffuse.a", "D3DTOP_BLENDDIFFUSEALPHA"),
)


def wired(source: str) -> bool:
    st = source.find("bool supported_game_state(")
    en = source.find("bool translate_vertices(", st)
    dr = source.find("bool submit(")
    de = source.find("void observe(", dr)
    if min(st, en, dr, de) < 0: return False
    gate, draw = source[st:en], source[dr:de]
    rgb = gate[gate.find("const bool rgbNeedsDiffuse"):gate.find("const bool alphaNeedsDiffuse")]
    alpha = gate[gate.find("const bool alphaNeedsDiffuse"):gate.find("if ((!modulate")]
    admitted = gate[gate.find("if ((!modulate"):gate.find("capture.addressU =")]
    for token in ('GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"',
                  "game->UpdateSurface(", "ctx->DrawIndexed(indexCount, 0, 0);",
                  "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
                  "mirror_texture(dev, capture, sampledView, sampledSampler)"):
        if token not in source: return False
    for name, mode, scale, factor, operation in VARIANTS:
        flag = f"blend{name}Modulate{mode}Alpha"
        shader = f"PSTextureBlend{name}Modulate{mode}Alpha"
        code = f"blend{name}Modulate{mode}Code"
        predicate = f"const bool {flag} = op == {operation} &&"
        pos = gate.find(predicate)
        if pos < 0 or f"alphaOp == D3DTOP_MODULATE{mode};" not in gate[pos:pos+165]:
            return False
        start = source.find(f"float4 {shader}(VOut v) : SV_Target {{")
        end = source.find("\n}", start)
        if start < 0 or end < 0: return False
        body = source[start:end]
        for tok in (f"lerp(v.diffuse.rgb, t.rgb, {factor})",
                    f"saturate({scale} * t.a * v.diffuse.a)",
                    "AlphaGate(c.a); return c;"):
            if tok not in body: return False
        for tok in (f"bool {flag} = false;",
                    f"ComPtr<ID3D11PixelShader> {flag}Ps;",
                    f"s.{flag}Ps &&",
                    f'compile("{shader}", "ps_4_0", {code})',
                    f"s.{flag}Ps.GetAddressOf()", f"capture.{flag} = {flag};"):
            if tok not in source: return False
        if source.count(f"s.{flag}Ps.Reset();") != 2: return False
        if f"capture.{flag} ? s.{flag}Ps.Get() :" not in draw: return False
        if flag not in rgb or flag not in alpha or f"!{flag} &&" not in admitted: return False
    return True


def run() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    assert wired(source), "00575 source-to-native pipeline broken"
    negative = 0
    for name, mode, scale, factor, op in VARIANTS:
        flag = f"blend{name}Modulate{mode}Alpha"
        shader = f"PSTextureBlend{name}Modulate{mode}Alpha"
        code = f"blend{name}Modulate{mode}Code"
        for token in (
            f"const bool {flag} = op == {op} &&",
            f"capture.{flag} = {flag};",
            f'compile("{shader}", "ps_4_0", {code})',
            f"s.{flag}Ps.GetAddressOf()",
            f"capture.{flag} ? s.{flag}Ps.Get() :",
            f"s.{flag}Ps &&", f"bool {flag} = false;",
        ):
            assert token in source
            assert not wired(source.replace(token, "/* sever 00575 */", 1)), token
            negative += 1
        predicate = f"const bool {flag} = op == {op} &&"
        p = source.index(predicate)
        alpha_op = f"alphaOp == D3DTOP_MODULATE{mode};"
        assert alpha_op in source[p:p+165]
        assert not wired(source[:p] + source[p:].replace(alpha_op, "alphaOp == D3DTOP_ADD;", 1))
        negative += 1
        st = source.index(f"float4 {shader}(VOut v) : SV_Target {{")
        en = source.index("\n}", st)
        body = source[st:en]
        for tok in (f"lerp(v.diffuse.rgb, t.rgb, {factor})",
                    f"saturate({scale} * t.a * v.diffuse.a)"):
            assert tok in body
            assert not wired(source[:st] + body.replace(tok, "/* wrong HLSL */", 1) + source[en:])
            negative += 1
    # D3D9 enums 12/13 RGB, 5/6 alpha; reject modifier bits/arg inversion.
    for op, alpha, arg1, arg2, accepted in (
        (12, 5, "texture", "diffuse", True),
        (13, 6, "texture", "current", True),
        (12, 6, "texture", "current", True),
        (13, 5, "texture", "diffuse", True),
        (14, 5, "texture", "diffuse", False),
        (13, 4, "texture", "diffuse", False),
        (13, 5, "texture|complement", "diffuse", False),
        (12, 6, "texture", "diffuse|complement", False),
        (12, 5, "diffuse", "diffuse", False),
        (13, 6, "texture", "texture", False),
    ):
        value = op in (12, 13) and alpha in (5, 6) and arg1 == "texture" and arg2 in ("diffuse", "current")
        assert value is accepted
    for ta, da in ((0.8, 0.6), (0.1, 0.2), (0.4, 0.7)):
        for scalar in (2, 4):
            actual = min(1.0, scalar * ta * da)
            assert 0 <= actual <= 1
            if ta == 0.8 and scalar == 2: assert abs(actual - 0.96) < 1e-9
            if ta == 0.8 and scalar == 4: assert actual == 1.0
    assert negative == 40
    print("DX11 00575 native game blend-scaled-alpha static PASS: 40 negative mutations; HMD UNTESTED")


if __name__ == "__main__":
    run()
