#!/usr/bin/env python3
"""00635: D3D9 PM RGB + complemented TFACTOR output alpha, native DX11 Draw."""
from itertools import product
from pathlib import Path

s = (Path(__file__).resolve().parents[1] /
     "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
arg1 = """const bool blendTextureAlphaPMInverseFactorArg1Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG1 &&
            alphaArg1 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT);"""
arg2 = """const bool blendTextureAlphaPMInverseFactorArg2Alpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_SELECTARG2 &&
            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT);"""
read = """if ((blendTextureAlphaPMInverseFactorArg1Alpha ||
             blendTextureAlphaPMInverseFactorArg2Alpha) &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;"""
arg2_guard = """const bool alphaArg2Diffuse = alphaArg2 == D3DTA_DIFFUSE || alphaArg2 == D3DTA_CURRENT ||
            blendTextureAlphaPMInverseFactorArg2Alpha;"""
capture_arg1 = """if (blendTextureAlphaPMInverseFactorArg1Alpha)
            capture.blendTextureAlphaPMFactorAlpha = true;"""
capture_arg2 = """if (blendTextureAlphaPMInverseFactorArg2Alpha) {
            capture.blendTextureAlphaPMDiffuseAlpha = false;
            capture.blendTextureAlphaPMFactorAlpha = true;
        }"""
factor = """capture.blendFactorAlphaValue = static_cast<float>((textureFactor >> 24u) & 0xffu) / 255.0f;
        if (blendTextureAlphaPMInverseFactorArg1Alpha || blendTextureAlphaPMInverseFactorArg2Alpha)
            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;"""
shader = "float4 PSTextureBlendTextureAlphaPMSelectFactorAlpha(VOut v) : SV_Target {"
pixel = "float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)), alphaParams.w);"
links = (arg1, arg2, read, arg2_guard, capture_arg1, capture_arg2, factor,
         "blendTextureAlphaPMFactorAlpha || blendTextureAlphaPMInverseFactorArg1Alpha || blendTextureAlphaPMInverseFactorArg2Alpha ||",
         "!blendTextureAlphaPMFactorAlpha && !blendTextureAlphaPMInverseFactorArg1Alpha && !blendTextureAlphaPMInverseFactorArg2Alpha &&",
         "!blendTextureAlphaPMInverseFactorArg1Alpha && !blendTextureAlphaPMInverseFactorArg2Alpha && alphaArg1 != D3DTA_TEXTURE",
         "capture.blendTextureAlphaPMFactorAlpha ? s.blendTextureAlphaPmFactorAlphaPs.Get() :",
         'compile("PSTextureBlendTextureAlphaPMSelectFactorAlpha", "ps_4_0", blendTexturePmFactorAlphaCode)',
         "s.blendTextureAlphaPmFactorAlphaPs.GetAddressOf()",
         "static_cast<float>(output.alphaFunc), capture.blendFactorAlphaValue",
         "ctx->UpdateSubresource(s.alphaConstants.Get(), 0, nullptr, alphaParams, 0, 0);",
         "ctx->PSSetConstantBuffers(0, 1, &alphaBuffer);",
         "ctx->DrawIndexed(indexCount, 0, 0);",
         "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
         'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"')

def connected(code: str) -> bool:
    if not all(link in code for link in links):
        return False
    if shader not in code:
        return False
    body = code.split(shader, 1)[1].split("}", 1)[0]
    if not all(item in body for item in (pixel, "AlphaGate(c.a); return c;")):
        return False
    return (code.index(arg1) < code.index(read) <
            code.index(capture_arg1) < code.index(capture_arg2) <
            code.index(factor) < code.index(links[10]) <
            code.index(links[16]))

assert connected(s), "live D3D9 capture / complemented factor / PM shader / native Draw disconnected"
for item in links[:7] + (links[10], links[13], links[14], links[15], shader, pixel):
    assert s.count(item) == 1, "ambiguous source mutation anchor: " + item[:70]
    assert not connected(s.replace(item, "BROKEN_00635", 1)), item[:70]
for predicate in (arg1, arg2):
    for bad in ("D3DTOP_BLENDTEXTUREALPHA", "D3DTA_TEXTURE | D3DTA_COMPLEMENT",
                "D3DTA_TFACTOR | D3DTA_ALPHAREPLICATE"):
        replacement = predicate.replace("D3DTOP_BLENDTEXTUREALPHAPM", bad, 1) if "D3DTOP_" in bad else predicate.replace("D3DTA_TFACTOR | D3DTA_COMPLEMENT", bad, 1)
        assert not connected(s.replace(predicate, replacement, 1))
# stage 0 PM=15; select alpha ARG1/ARG2=2/3; TFACTOR=3, COMPLEMENT=0x10
def admitted(rgb_op, alpha_op, a1, a2):
    return rgb_op == 15 and ((alpha_op == 2 and a1 == 0x13) or
                             (alpha_op == 3 and a2 == 0x13))
for op, alpha_op, a1, a2 in product((12, 15), (2, 3, 4),
                                    (0, 3, 16, 19, 35), (0, 3, 16, 19, 35)):
    assert admitted(op, alpha_op, a1, a2) == (
        op == 15 and ((alpha_op == 2 and a1 == 19) or
                      (alpha_op == 3 and a2 == 19)))
# Original texture A still weights RGB, while COMPLEMENT acts on the actual
# game TFACTOR high byte. Both 0/255 endpoints and interior bytes are exact.
different = 0
for tex, vertex, sample_alpha, factor_byte in product(
        (0.0, 0.25, 0.75, 1.0), (0.0, 0.3, 0.7, 1.0),
        (0.0, 0.25, 0.75, 1.0), range(256)):
    rgb = min(1.0, tex + vertex * (1.0 - sample_alpha))
    alpha = 1.0 - factor_byte / 255.0
    assert 0.0 <= rgb <= 1.0 and 0.0 <= alpha <= 1.0
    if abs(alpha - sample_alpha) > 1e-6:
        different += 1
assert different > 0
print("00635 complemented PM factor: native capture/constant/PS/Draw, destructive "
      "and 16384 numerical combinations PASS; Quest3/VDXR UNTESTED")
