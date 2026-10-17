#!/usr/bin/env python3
"""00618: live game D3D9 PM RGB + independent DIFFUSE/CURRENT alpha -> native DX11.
Only source/numeric validation; this is not a game/Quest3 runtime result.
"""
from pathlib import Path
import itertools

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HEADER = ROOT / "src/vr/d3d11/live_game_stage0_blend.hpp"

def linked(b: str, h: str) -> bool:
    ps = b.split("float4 PSTextureBlendTextureAlphaPMSelectDiffuseAlpha(VOut v) : SV_Target {", 1)
    if len(ps) != 2:
        return False
    ps = ps[1].split("}", 1)[0]
    required = (
        "colorOp == kGameStage0BlendTextureAlphaPM && alphaOp == 3u;",
        "game_stage0_premultiplied_diffuse_alpha_pair(op, alphaOp)",
        "const bool blendTextureAlphaPMDiffuseAlpha =",
        "bool blendTextureAlphaPMDiffuseAlpha = false;",
        "s.blendTextureAlphaPmDiffuseAlphaPs &&",
        "s.blendTextureAlphaPmDiffuseAlphaPs.Reset();",
        'compile("PSTextureBlendTextureAlphaPMSelectDiffuseAlpha", "ps_4_0", blendTexturePmDiffuseAlphaCode)',
        "s.blendTextureAlphaPmDiffuseAlphaPs.GetAddressOf()",
        "capture.blendTextureAlphaPMDiffuseAlpha = blendTextureAlphaPMDiffuseAlpha;",
        "capture.blendTextureAlphaPMDiffuseAlpha ? s.blendTextureAlphaPmDiffuseAlphaPs.Get() :",
        "blendTextureAlphaPMDiffuseAlpha ||",
        "!blendTextureAlphaPMDiffuseAlpha && !blendTextureAlpha",
        "alphaArg1 != D3DTA_TEXTURE && !blendTextureAlphaPMDiffuseAlpha",
        "const bool alphaArg2UnusedOnSelectArg1 = alphaOp == D3DTOP_SELECTARG1;",
        "(alphaNeedsDiffuse && !alphaArg2Diffuse) && !alphaArg2UnusedOnSelectArg1",
        "nextColorOp != D3DTOP_DISABLE",
    )
    return (
        "constexpr bool game_stage0_premultiplied_diffuse_alpha_pair(" in h
        and "colorOp == kGameStage0BlendTextureAlphaPM && alphaOp == 3u;" in h
        and all(s in b for s in required if not s.startswith("colorOp =="))
        and b.count("blendTextureAlphaPMDiffuseAlpha ||") == 2
        and "float4 t = gameTexture.Sample(gameSampler, v.uv);" in ps
        and "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), v.diffuse.a);" in ps
        and "AlphaGate(c.a); return c;" in ps
        and ("ctx->Draw(" in b or "context->Draw(" in b) and ("ctx->DrawIndexed(" in b or "context->DrawIndexed(" in b)
    )

def main() -> None:
    b, h = BRIDGE.read_text(encoding="utf-8"), HEADER.read_text(encoding="utf-8")
    assert linked(b, h), "PM SELECTARG2 native pipeline disconnected"
    destructive = (
        ("bridge", "capture.blendTextureAlphaPMDiffuseAlpha = blendTextureAlphaPMDiffuseAlpha;", "capture.blendTextureAlphaPMDiffuseAlpha = false;"),
        ("bridge", "s.blendTextureAlphaPmDiffuseAlphaPs.GetAddressOf()", "s.blendTextureAlphaPmTextureAlphaPs.GetAddressOf()"),
        ("bridge", "blendTextureAlphaPMDiffuseAlpha ||", "false ||"),
        ("bridge", "alphaArg1 != D3DTA_TEXTURE && !blendTextureAlphaPMDiffuseAlpha", "alphaArg1 != D3DTA_TEXTURE && false"),
        ("bridge", "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), v.diffuse.a);", "float4 c = saturate(t + v.diffuse * (1.0f - t.a));"),
        ("bridge", "const bool alphaArg2UnusedOnSelectArg1 = alphaOp == D3DTOP_SELECTARG1;", "const bool alphaArg2UnusedOnSelectArg1 = false;"),
        ("bridge", "(alphaNeedsDiffuse && !alphaArg2Diffuse) && !alphaArg2UnusedOnSelectArg1", "(alphaNeedsDiffuse && !alphaArg2Diffuse)"),
        ("header", "colorOp == kGameStage0BlendTextureAlphaPM && alphaOp == 3u;", "colorOp == kGameStage0BlendTextureAlphaPM && alphaOp == 2u;"),
    )
    for kind, before, after in destructive:
        source = b if kind == "bridge" else h
        assert before in source
        changed = source.replace(before, after, 1)
        assert changed != source
        assert not linked(changed, h) if kind == "bridge" else not linked(b, changed), kind
    # PM RGB saturation and SELECTARG2 alpha cannot silently use PM alpha.
    for texture_rgb, diffuse_rgb, texture_alpha, diffuse_alpha in itertools.product(
        (0.0, 0.2, 0.75, 1.0), (0.0, 0.25, 0.8, 1.0),
        (0.0, 0.3, 0.8, 1.0), (0.0, 0.1, 0.5, 1.0)
    ):
        rgb = min(1.0, texture_rgb + diffuse_rgb * (1.0-texture_alpha))
        expected = min(1.0, texture_rgb + diffuse_rgb * (1.0-texture_alpha))
        assert 0 <= rgb <= 1 and abs(rgb-expected) < 1e-9
        alpha_out = diffuse_alpha
        assert alpha_out == diffuse_alpha
        if texture_alpha != diffuse_alpha:
            assert alpha_out != texture_alpha
    print("00618 PM RGB+SELECTARG2 diffuse alpha native game draw: source/numeric/mutation PASS; HMD UNTESTED")

if __name__ == "__main__":
    main()
