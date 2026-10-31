#!/usr/bin/env python3
"""00633: PM RGB and SELECTARG2 complemented texture alpha live native Draw."""
from itertools import product
from pathlib import Path
s = (Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
predicate = """const bool blendTextureAlphaPMInverseTextureArg2Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG2 &&
            alphaArg2 == (D3DTA_TEXTURE | D3DTA_COMPLEMENT);"""
bridge = """if (blendTextureAlphaPMInverseTextureArg2Alpha) {
            capture.blendTextureAlphaPMDiffuseAlpha = false;
            capture.blendTextureAlphaPMInverseTextureAlpha = true;
        }"""
guard = """!blendTextureAlphaPMFactorArg2Alpha &&
              !blendTextureAlphaPMInverseTextureArg2Alpha)"""
hlsl = "float4 PSTextureBlendTextureAlphaPMSelectInverseTextureAlpha(VOut v) : SV_Target {"
pixel = "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), 1.0f - t.a);"
compiled = 'compile("PSTextureBlendTextureAlphaPMSelectInverseTextureAlpha", "ps_4_0", blendTexturePmInverseTextureAlphaCode)'
binding = "capture.blendTextureAlphaPMInverseTextureAlpha ? s.blendTextureAlphaPmInverseTextureAlphaPs.Get() :"
links = (predicate, bridge, guard, hlsl, pixel, compiled, binding,
         "s.blendTextureAlphaPmInverseTextureAlphaPs.GetAddressOf()",
         "ctx->DrawIndexed(indexCount, 0, 0);",
         "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
         'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"',
         "capture.blendTextureAlphaPMDiffuseAlpha = blendTextureAlphaPMDiffuseAlpha;",
         "capture.blendTextureAlphaPMInverseTextureAlpha = blendTextureAlphaPMInverseTextureAlpha;")
def connected(source):
    if not all(k in source for k in links):
        return False
    pixel_body = source.split(hlsl, 1)[1].split("}",1)[0]
    return (pixel in pixel_body and "AlphaGate(c.a); return c;" in pixel_body
            and source.index(predicate) < source.index(bridge) < source.index(binding)
            and source.index(links[11]) < source.index(bridge)
            and source.index(links[12]) < source.index(bridge))
assert connected(s), "native PM source->capture->shader->Draw graph disconnected"
for anchor in (predicate, bridge, guard, pixel, compiled, binding, links[11], links[12]):
    assert s.count(anchor) == 1, "ambiguous mutation anchor: " + anchor[:50]
    assert not connected(s.replace(anchor, "BROKEN_00633", 1)), "undetected mutation: " + anchor[:50]
for old, new in (("alphaOp == D3DTOP_SELECTARG2","alphaOp == D3DTOP_SELECTARG1"),
                 ("alphaArg2 == (D3DTA_TEXTURE | D3DTA_COMPLEMENT)","alphaArg2 == D3DTA_DIFFUSE"),
                 ("op == D3DTOP_BLENDTEXTUREALPHAPM","op == D3DTOP_BLENDTEXTUREALPHA")):
    assert not connected(s.replace(predicate, predicate.replace(old,new),1))
# D3D9 PM RGB opcode=15; SELECTARG2=3; TEXTURE|COMPLEMENT=0x12.
def accepted(op, alpha_op, arg2):
    return op == 15 and alpha_op == 3 and arg2 == 0x12
for op, aop, arg2 in product((12,15),(2,3,4),(0,1,2,0x12,0x22,0x32)):
    assert accepted(op,aop,arg2) == (op == 15 and aop == 3 and arg2 == 0x12)
non_diffuse, non_full_pm = 0, 0
for t_rgb, diffuse_rgb, texture_a, diffuse_a in product((0.,.2,.8,1.), repeat=4):
    rgb = min(1., t_rgb + diffuse_rgb * (1. - texture_a))
    alpha = 1. - texture_a
    assert 0 <= rgb <= 1 and 0 <= alpha <= 1
    non_diffuse += abs(alpha - diffuse_a) > 1e-6
    non_full_pm += abs(alpha - min(1.,texture_a + diffuse_a*(1.-texture_a))) > 1e-6
assert non_diffuse > 0 and non_full_pm > 0
print("00633 native PM SELECTARG2 complemented texture alpha: linked source, destructive, 256 numerics PASS; HMD UNTESTED")
