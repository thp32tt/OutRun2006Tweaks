#!/usr/bin/env python3
"""Stage1 premultiplied texture menu/race game->shader->Draw regression, TASK 00711."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
h=(r/"src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
b=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
w=(r/".github/workflows/dx11-fast-structural.yml").read_text()
p=(r/"tools/dx11_game_stage1_premultiplied_probe_00711.cpp").read_text()
def integrated(h,b):
    shader=b.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
    gate=b.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    draw=b.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
    return all(x in h for x in ("kStage1BlendTextureAlphaPM = 15u","op == kStage1BlendTextureAlphaPM) && matchedTextureSampler &&")) and all(x in b for x in ("kStage1BlendTextureAlphaPM == D3DTOP_BLENDTEXTUREALPHAPM",)) and all(x in shader for x in (
        "if (stage1Ops.x == 15)","if (stage1Ops.y == 15)",
        "color = saturate(pmColor1 + pmColor2 * (1.0f - stage1TextureAlpha));",
        "alpha = saturate(pmAlpha1 + pmAlpha2 * (1.0f - stage1TextureAlpha)).a;",
        "float4 pmColor1 = Stage1Source(stage0, diffuse, specular, stage1Args.x);",
        "float4 pmAlpha1 = Stage1Source(stage0, diffuse, specular, stage1Args.z);",
        "AlphaGate(result.a);")) and all(x in gate for x in (
        "nextColorOp == D3DTOP_BLENDTEXTUREALPHAPM","alphaOp == D3DTOP_BLENDTEXTUREALPHAPM",
        "stage1_matched_texture_alpha_blend_supported(",
        "tex1.Get() != tex.Get()","uv1 != capture.coordIndex",
        "std::memcmp(&capture.uvTransform, &matrix1, sizeof(matrix1)) != 0",
        "game->GetSamplerState(0, state, &s0)","game->GetSamplerState(1, state, &s1)",
        "s0 != s1","D3DSAMP_SRGBTEXTURE")) and all(x in draw for x in (
        "ctx->PSSetConstantBuffers(1, 1, &combiner)","ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
assert integrated(h,b)
for s in ("op == kStage1BlendTextureAlphaPM) && matchedTextureSampler &&",
    "nextColorOp == D3DTOP_BLENDTEXTUREALPHAPM","alphaOp == D3DTOP_BLENDTEXTUREALPHAPM",
    "if (stage1Ops.x == 15)","if (stage1Ops.y == 15)",
    "color = saturate(pmColor1 + pmColor2 * (1.0f - stage1TextureAlpha));",
    "alpha = saturate(pmAlpha1 + pmAlpha2 * (1.0f - stage1TextureAlpha)).a;",
    "tex1.Get() != tex.Get()","s0 != s1"):
    if s in h: assert not integrated(h.replace(s,"",1),b),s
    else: assert not integrated(h,b.replace(s,"",1)),s
assert "regular!=400u || temp!=160u || pairs!=4u" in p
assert "python tools/test_dx11_stage1_premultiplied_00711.py" in w
assert "tools/dx11_game_stage1_premultiplied_probe_00711.cpp" in w
print("PASS 00711 premultiplied Stage1 RGB/alpha native Draw/Indexed and mismatch rejection")
