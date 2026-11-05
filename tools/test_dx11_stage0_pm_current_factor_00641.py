#!/usr/bin/env python3
"""00641 D3D9 CURRENT-weighted texture/factor alpha into native Draw."""
from pathlib import Path
from itertools import product
s=(Path(__file__).resolve().parents[1]/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
pred="""const bool blendTextureAlphaPMBlendCurrentFactorAlpha =
            op == D3DTOP_BLENDTEXTUREALPHAPM &&
            alphaOp == D3DTOP_BLENDCURRENTALPHA &&
            alphaArg1 == D3DTA_TEXTURE &&
            (alphaArg2 == D3DTA_TFACTOR ||
             alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT));"""
shader="""float4 PSTextureBlendTextureAlphaPMBlendCurrentFactorAlpha(VOut v) : SV_Target {
    float4 t = gameTexture.Sample(gameSampler, v.uv);
    float4 c = float4(saturate(t.rgb + v.diffuse.rgb * (1.0f - t.a)),
                      lerp(alphaParams.w, t.a, v.diffuse.a));
    AlphaGate(c.a); return c;
}"""
read="""if (blendTextureAlphaPMBlendCurrentFactorAlpha &&
            FAILED(game->GetRenderState(D3DRS_TEXTUREFACTOR, &textureFactor)))
            return false;"""
inverse="""if (blendTextureAlphaPMBlendCurrentFactorAlpha &&
            alphaArg2 == (D3DTA_TFACTOR | D3DTA_COMPLEMENT))
            capture.blendFactorAlphaValue = 1.0f - capture.blendFactorAlphaValue;"""
graph=[pred,shader,read,inverse,
"if (blendTextureAlphaPMBlendCurrentFactorAlpha && !arg2Diffuse) return false;",
"!blendTextureAlphaPMBlendCurrentFactorAlpha &&",
"capture.blendTextureAlphaPMBlendCurrentFactorAlpha = blendTextureAlphaPMBlendCurrentFactorAlpha;",
'compile("PSTextureBlendTextureAlphaPMBlendCurrentFactorAlpha", "ps_4_0", blendTexturePmBlendCurrentFactorAlphaCode)',
"s.blendTextureAlphaPmBlendCurrentFactorAlphaPs.GetAddressOf()",
"capture.blendTextureAlphaPMBlendCurrentFactorAlpha ? s.blendTextureAlphaPmBlendCurrentFactorAlphaPs.Get() :",
"s.blendTextureAlphaPmBlendCurrentFactorAlphaPs &&",
"s.blendTextureAlphaPmBlendCurrentFactorAlphaPs.Reset();",
"ctx->DrawIndexed(indexCount, 0, 0);",
"ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
"OUTRUN_DX11_FIRST_GAME_FRAME"]
def connected(v):
 return all(x in v for x in graph) and v.index(pred)<v.index(read)<v.index(graph[6])<v.index(graph[9])
assert connected(s)
for x in graph[:12]:
 assert not connected(s.replace(x,"BROKEN_00641")),x[:65]
for x,y in [("D3DTOP_BLENDCURRENTALPHA","D3DTOP_BLENDDIFFUSEALPHA"),("alphaArg1 == D3DTA_TEXTURE","alphaArg1 == D3DTA_TFACTOR"),("alphaArg2 == D3DTA_TFACTOR","alphaArg2 == D3DTA_TEXTURE"),("D3DTOP_BLENDTEXTUREALPHAPM","D3DTOP_BLENDTEXTUREALPHA")]:
 assert not connected(s.replace(pred,pred.replace(x,y),1))
n=0
for ta,da,fa,complement in product((0.,.13,.5,.87,1.),(0.,.25,.5,.75,1.),range(256),(False,True)):
 factor=fa/255.
 if complement: factor=1.-factor
 oracle=ta*da+factor*(1.-da)
 native=factor+da*(ta-factor)
 assert abs(oracle-native)<1e-12 and 0.<=native<=1.
 rgb=min(1.,.3+.6*(1.-ta))
 assert 0.<=rgb<=1.
 n+=1
assert n==12800
assert abs((.9*.25+.2*.75)-(.9*.8+.25*.2))>.1  # Wrong interpolation weight / operand order
print("00641 PM CURRENT TFACTOR source/native Draw + 12800 numeric PASS; HMD UNTESTED")
