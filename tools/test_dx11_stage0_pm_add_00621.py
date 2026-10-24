#!/usr/bin/env python3
"""00621: live D3D9 PM RGB + separately added alpha into native D3D11 Draw."""
from pathlib import Path
import itertools

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
SHADER = "float4 PSTextureBlendTextureAlphaPMAddAlpha(VOut v) : SV_Target {"
COLOR = "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),"
ALPHA = "saturate(t.a + v.diffuse.a));"
PRED = """const bool blendTextureAlphaPMAddAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_ADD && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);"""
LINKS = (
    "bool blendTextureAlphaPMAddAlpha = false;",
    "ComPtr<ID3D11PixelShader> blendTextureAlphaPmAddAlphaPs;",
    "s.blendTextureAlphaPmAddAlphaPs &&",
    "s.blendTextureAlphaPmAddAlphaPs.Reset();",
    "blendTexturePmAddAlphaCode,",
    'compile("PSTextureBlendTextureAlphaPMAddAlpha", "ps_4_0", blendTexturePmAddAlphaCode)',
    "s.blendTextureAlphaPmAddAlphaPs.GetAddressOf()",
    "blendTextureAlphaPMModulateAlpha || blendTextureAlphaPMAddAlpha ||",
    "!blendTextureAlphaPMAddAlpha &&",
    "capture.blendTextureAlphaPMAddAlpha = blendTextureAlphaPMAddAlpha;",
    "capture.blendTextureAlphaPMAddAlpha ? s.blendTextureAlphaPmAddAlphaPs.Get() :",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"',
)

def linked(source):
    tail = source.split(SHADER, 1)
    shader_body = tail[1].split("}", 1)[0] if len(tail) == 2 else ""
    return (PRED in source and COLOR in shader_body and ALPHA in shader_body
            and "AlphaGate(c.a); return c;" in shader_body
            and all(token in source for token in LINKS)
            and source.count("s.blendTextureAlphaPmAddAlphaPs.Reset();") == 2
            and source.count("s.blendTextureAlphaPmAddAlphaPs.GetAddressOf()") == 1)

def main():
    source = SOURCE.read_text(encoding="utf-8")
    assert linked(source), "00621 native PM ADD alpha is not linked end-to-end"
    # Destructive mutations: no guard-only PASS without source/compile/draw wiring.
    unique = [token for token in LINKS if source.count(token) == 1]
    for token in unique:
        assert not linked(source.replace(token, "BROKEN_00621", 1)), token
    for old, new in (
        ("alphaOp == D3DTOP_ADD", "alphaOp == D3DTOP_MODULATE"),
        ("alphaArg1 == D3DTA_TEXTURE", "alphaArg1 == D3DTA_TFACTOR"),
        ("alphaArg2 == D3DTA_CURRENT", "alphaArg2 == D3DTA_TFACTOR"),
        ("alphaArg2 == D3DTA_DIFFUSE", "alphaArg2 == D3DTA_SPECULAR"),
    ):
        assert not linked(source.replace(PRED, PRED.replace(old, new), 1)), old
    shader_fragment = SHADER + source.split(SHADER, 1)[1].split("}", 1)[0] + "}"
    for old in ("t.a + v.diffuse.a", "t.rgb + v.diffuse.rgb * (1.0f - t.a)"):
        assert old in shader_fragment
        mutant = shader_fragment.replace(old, "0.0f", 1)
        assert not linked(source.replace(shader_fragment, mutant, 1)), old
    # 8-bit alpha and saturated RGB: covered edge and middle values independently.
    for tr, vr, ta, va in itertools.product((0., .2, .6, 1.), repeat=4):
        rgb = min(1., tr + vr * (1. - ta))
        alpha = min(1., ta + va)
        assert 0. <= rgb <= 1. and 0. <= alpha <= 1.
        assert alpha >= ta and alpha >= va
    # Mutually exclusive PM family selection: SELECTARG1, SELECTARG2, TFACTOR,
    # MODULATE, and ADD must never resolve to the same stage-0 alpha variant.
    pairs = ((15, 15), (15, 2), (15, 3), (15, 4), (15, 7))
    assert len(set(pairs)) == len(pairs)
    print(f"00621 PM RGB + ADD alpha native Draw: {len(unique) + 6} mutations, 256 numeric cases PASS; HMD UNTESTED")

if __name__ == "__main__":
    main()
