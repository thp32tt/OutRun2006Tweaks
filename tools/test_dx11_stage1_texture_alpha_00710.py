#!/usr/bin/env python3
"""DX11 00710 Stage1 same-texture alpha/native game Draw static mutation regressions."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
h=(r/"src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
b=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
w=(r/".github/workflows/dx11-fast-structural.yml").read_text()
p=(r/"tools/dx11_game_stage1_texture_alpha_probe_00710.cpp").read_text()
def integrated(h,b):
    sh=b.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
    state=b.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    draw=b.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
    return all(s in h for s in ("kStage1BlendTextureAlpha = 13u",
        "stage1_matched_texture_alpha_blend_supported(",
        "matchedTextureSampler &&")) and all(s in state for s in (
        "nextColorOp == D3DTOP_BLENDTEXTUREALPHA",
        "alphaOp == D3DTOP_BLENDTEXTUREALPHA",
        "stage1_matched_texture_alpha_blend_supported(",
        "tex1.Get() != tex.Get()",
        "uv1 != capture.coordIndex",
        "transform1 != (capture.transformUv ? D3DTTFF_COUNT2 : D3DTTFF_DISABLE)",
        "std::memcmp(&capture.uvTransform, &matrix1, sizeof(matrix1)) != 0",
        "game->GetSamplerState(0, state, &s0)",
        "game->GetSamplerState(1, state, &s1)",
        "s0 != s1",
        "D3DSAMP_SRGBTEXTURE",
        "capture.stage1ColorOp = nextColorOp;",
        "capture.stage1AlphaOp = alphaOp;")) and all(s in sh for s in (
        "stage1Ops.x == 13",
        "stage1Ops.y == 13",
        "stage1TextureAlpha));",
        "float4 t = gameTexture.Sample(gameSampler, v.uv);",
        "v.diffuse, v.specular, t.a);",
        "AlphaGate(result.a);")) and sh.count("stage1TextureAlpha));") == 2 and all(s in draw for s in (
        "ctx->PSSetConstantBuffers(1, 1, &combiner)",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")) and (
        "kStage1BlendTextureAlpha == D3DTOP_BLENDTEXTUREALPHA" in b)
assert integrated(h,b)
for s in ("tex1.Get() != tex.Get()","uv1 != capture.coordIndex",
          "s0 != s1","stage1Ops.x == 13","stage1Ops.y == 13",
          "stage1TextureAlpha));","ctx->DrawIndexed(indexCount, 0, 0);"):
    assert not integrated(h,b.replace(s,"",1)),s
assert not integrated(h.replace("matchedTextureSampler &&","true &&",1),b)
assert "regular!=400u || temp!=160u" in p
assert "python tools/test_dx11_stage1_texture_alpha_00710.py" in w
assert "tools/dx11_game_stage1_texture_alpha_probe_00710.cpp" in w
print("PASS 00710 matched Stage1 texture alpha -> native Draw/Indexed; mismatch fallback")
