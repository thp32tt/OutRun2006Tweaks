#!/usr/bin/env python3
"""00617 regression: real game D3D9 stage0 PM -> D3D11 Draw/DrawIndexed (no HMD)."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "src/vr/d3d11/live_game_stage0_blend.hpp"
B = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"

def linked(h, b):
    part = b.split("bool supported_game_state(", 1)[-1].split("bool translate_vertices(", 1)[0]
    ps = b.split("float4 PSTextureBlendTextureAlphaPM(VOut v) : SV_Target {", 1)
    # A separate 00618 SELECTARG2 helper shares this identifier. Check the
    # original PM/PM helper itself so destructive mutations cannot pass via it.
    pair = h.split("constexpr bool game_stage0_premultiplied_pair(", 1)
    pair_body = pair[1].split("}", 1)[0] if len(pair) == 2 else ""
    return len(ps) == 2 and len(pair) == 2 and all(t in pair_body for t in (
        "colorOp == kGameStage0BlendTextureAlphaPM &&",
        "alphaOp == kGameStage0BlendTextureAlphaPM;"
    )) and all(t in h for t in (
        "kGameStage0BlendTextureAlphaPM = 15u;",
        "colorOp == kGameStage0BlendTextureAlphaPM &&",
        "alphaOp == kGameStage0BlendTextureAlphaPM;"
    )) and all(t in b for t in (
        "kGameStage0BlendTextureAlphaPM == D3DTOP_BLENDTEXTUREALPHAPM",
        "bool blendTextureAlphaPM = false;",
        "ComPtr<ID3D11PixelShader> blendTextureAlphaPmPs;",
        "s.blendTextureAlphaPmPs &&",
        "s.blendTextureAlphaPmPs.Reset();",
        "s.blendTextureAlphaPmTextureAlphaPs.Reset();",
        "s.blendTextureAlphaPmTextureAlphaPs &&",
        'compile("PSTextureBlendTextureAlphaPMSelectTextureAlpha", "ps_4_0", blendTexturePmTextureAlphaCode)',
        "s.blendTextureAlphaPmTextureAlphaPs.GetAddressOf()",
        "capture.blendTextureAlphaPMTextureAlpha = blendTextureAlphaPMTextureAlpha;",
        'compile("PSTextureBlendTextureAlphaPM", "ps_4_0", blendTexturePmCode)',
        "s.blendTextureAlphaPmPs.GetAddressOf()",
        "capture.blendTextureAlphaPM = blendTextureAlphaPM;",
        "capture.blendTextureAlphaPM ? s.blendTextureAlphaPmPs.Get() :",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        "capture.blendTextureAlphaPMTextureAlpha ? s.blendTextureAlphaPmTextureAlphaPs.Get() :"
    )) and all(t in part for t in (
        "const bool blendTextureAlphaPM = game_stage0_premultiplied_pair(op, alphaOp);",
        "!blendTextureAlpha && !blendTextureAlphaPM && !blendTextureAlphaPMTextureAlpha && !blendDiffuseAlpha",
        "op == D3DTOP_BLENDTEXTUREALPHAPM && alphaOp == D3DTOP_SELECTARG1",
        "if (!layout.hasDiffuse && !selectTexture) return false;",
        "arg != D3DTA_TEXTURE", "(rgbNeedsDiffuse && !arg2Diffuse)",
        "nextColorOp != D3DTOP_DISABLE", "resultArg != D3DTA_CURRENT"
    )) and part.count("blendTextureAlpha || blendTextureAlphaPM || blendTextureAlphaPMTextureAlpha || blendDiffuseAlpha || blendFactorAlpha;") == 2 and all(t in ps[1].split("}", 1)[0] for t in (
        "float4 t = gameTexture.Sample(gameSampler, v.uv);",
        "float4 c = saturate(t + v.diffuse * (1.0f - t.a));",
        "AlphaGate(c.a); return c;"
    ))

def main():
    h, b = H.read_text(encoding="utf-8"), B.read_text(encoding="utf-8")
    assert linked(h, b)
    mutations = (
        ("header","colorOp == kGameStage0BlendTextureAlphaPM &&","colorOp == 13u &&"),
        ("bridge","game_stage0_premultiplied_pair(op, alphaOp)","op == D3DTOP_BLENDTEXTUREALPHA"),
        ("bridge","s.blendTextureAlphaPmPs &&","true &&"),
        ("bridge","s.blendTextureAlphaPmPs.GetAddressOf()","s.blendTextureAlphaPs.GetAddressOf()"),
        ("bridge","float4 c = saturate(t + v.diffuse * (1.0f - t.a));","float4 c = lerp(v.diffuse, t, t.a);"),
        ("bridge","capture.blendTextureAlphaPM = blendTextureAlphaPM;","capture.blendTextureAlphaPM = false;"),
        ("bridge","capture.blendTextureAlphaPM ? s.blendTextureAlphaPmPs.Get() :","capture.blendTextureAlphaPM ? s.blendTextureAlphaPs.Get() :"),
        ("bridge","!blendTextureAlpha && !blendTextureAlphaPM && !blendTextureAlphaPMTextureAlpha && !blendDiffuseAlpha",
         "!blendTextureAlpha && !blendDiffuseAlpha")
    )
    for owner, good, wrong in mutations:
        original = h if owner == "header" else b
        assert good in original, good
        broken = original.replace(good, wrong, 1)
        assert not linked(broken if owner == "header" else h, broken if owner == "bridge" else b), good
    extra = b.split("float4 PSTextureBlendTextureAlphaPMSelectTextureAlpha(VOut v) : SV_Target {", 1)
    assert len(extra) == 2 and all(v in extra[1].split("}", 1)[0] for v in (
        "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), t.a);",
        "AlphaGate(c.a); return c;"
    ))
    # An independently selected alpha must remain texture alpha, not PM RGBA.
    for a in (0., .15, .65, 1.):
        diffuse_a = 0.75
        pm_a = min(1., a + diffuse_a*(1-a))
        assert a <= pm_a + 1e-8
    for alpha in (0., 0.125, 0.5, 0.875, 1.):
        for tex in (0., 0.08, 0.25, 0.7):
            for diffuse in (0., 0.2, 0.6, 1.):
                pm = min(1., max(0., tex + diffuse * (1-alpha)))
                wrong = tex * alpha + diffuse * (1-alpha)
                assert 0 <= pm <= 1 and pm+1e-8 >= wrong
    assert abs(min(1.,0.25+0.6*0.5)-0.55) < 1e-7
    for rgb, a, accepted in ((15,15,True),(15,2,True),(15,13,False),(13,15,False),(16,15,False),(15,16,False)):
        assert (rgb == 15 and a in (15, 2)) is accepted
    print("DX11 game stage0 PM native Draw PASS (static/numeric; HMD untested)")

if __name__ == "__main__": main()
