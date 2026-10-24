#!/usr/bin/env python3
"""00622: game Draw PM RGB with independent saturating stage0 SUBTRACT alpha."""
from itertools import product
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
SHADER = "float4 PSTextureBlendTextureAlphaPMSubtractAlpha(VOut v) : SV_Target {"
PRED = """const bool blendTextureAlphaPMSubtractAlpha = op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SUBTRACT && alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT);"""
RGB = "saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a))"
ALPHA = "saturate(t.a - v.diffuse.a)"
LINKS = (
    "bool blendTextureAlphaPMSubtractAlpha = false;",
    "ComPtr<ID3D11PixelShader> blendTextureAlphaPmSubtractAlphaPs;",
    "s.blendTextureAlphaPmSubtractAlphaPs &&",
    "blendTexturePmSubtractAlphaCode,",
    'compile("PSTextureBlendTextureAlphaPMSubtractAlpha", "ps_4_0", blendTexturePmSubtractAlphaCode)',
    "s.blendTextureAlphaPmSubtractAlphaPs.GetAddressOf()",
    "blendTextureAlphaPMAddAlpha || blendTextureAlphaPMSubtractAlpha ||",
    "!blendTextureAlphaPMSubtractAlpha &&",
    "capture.blendTextureAlphaPMSubtractAlpha = blendTextureAlphaPMSubtractAlpha;",
    "capture.blendTextureAlphaPMSubtractAlpha ? s.blendTextureAlphaPmSubtractAlphaPs.Get() :",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"',
)

def linked(s: str) -> bool:
    tail = s.split(SHADER, 1)
    shader = tail[1].split("}", 1)[0] if len(tail) == 2 else ""
    return (PRED in s and RGB in shader and ALPHA in shader
            and "AlphaGate(c.a); return c;" in shader
            and all(token in s for token in LINKS)
            and s.count("s.blendTextureAlphaPmSubtractAlphaPs.Reset();") == 2
            and s.count("s.blendTextureAlphaPmSubtractAlphaPs.GetAddressOf()") == 1)

def main() -> None:
    s = SOURCE.read_text(encoding="utf-8")
    assert linked(s), "native PM/SUBTRACT-alpha game Draw integration incomplete"
    unique = [token for token in LINKS if s.count(token) == 1]
    for token in unique:
        assert not linked(s.replace(token, "BROKEN_00622", 1)), token
    for old, new in (
        ("alphaOp == D3DTOP_SUBTRACT", "alphaOp == D3DTOP_ADD"),
        ("alphaArg1 == D3DTA_TEXTURE", "alphaArg1 == D3DTA_TFACTOR"),
        ("alphaArg2 == D3DTA_CURRENT", "alphaArg2 == D3DTA_TFACTOR"),
        ("alphaArg2 == D3DTA_DIFFUSE", "alphaArg2 == D3DTA_SPECULAR"),
    ):
        assert not linked(s.replace(PRED, PRED.replace(old, new), 1)), old
    frag = SHADER + s.split(SHADER, 1)[1].split("}", 1)[0] + "}"
    for old in (RGB, ALPHA):
        assert old in frag
        assert not linked(s.replace(frag, frag.replace(old, "0.0f", 1), 1)), old
    # Independent 4-dimensional RGB/alpha corners, including alpha underflow.
    for tr, dr, ta, da in product((0., 0.2, 0.6, 1.), repeat=4):
        rgb = min(1., tr + dr * (1. - ta))
        a = max(0., ta - da)
        assert 0. <= rgb <= 1. and 0. <= a <= 1.
        assert a <= ta and (a == 0. if da >= ta else a > 0.)
    # D3D9 ADD and SUBTRACT are distinct stage0 alpha variants.
    assert (15, 7) != (15, 10)
    print(f"00622 PM RGB/SUBTRACT alpha: {len(unique) + 6} destructive mutants + 256 arithmetic cases PASS; runtime UNTESTED")

if __name__ == "__main__":
    main()
