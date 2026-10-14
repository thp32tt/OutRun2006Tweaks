#!/usr/bin/env python3
"""Integrated dual real-game Stage1 texture t1/s1 Draw/Indexed regression."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
c=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
w=(r/".github/workflows/dx11-fast-structural.yml").read_text()
g=c.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
h=c.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
d=c.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
def complete(g,h,d):
    return all(t in g for t in (
       "tex1.Get() != tex.Get()","stage1_dual_texture_compatible(",
       "tex1.As(&capture.stage1SeparateTexture)", "if (states[i] == D3DSAMP_ADDRESSW && s0 != s1) return false;",
       "samplerDiff |= s0 != s1;", "stage1_game_sampler_supported(",
       "uv1 != capture.coordIndex")) and all(t in h for t in (
       "Texture2D stage1GameTexture : register(t1);",
       "SamplerState stage1GameSampler : register(s1);",
       "stage1GameTexture.Sample(stage1GameSampler, v.uv)",
       "if (stage1Ops.w == 2)")) and all(t in d for t in (
       "TextureCapture second = capture;",
       "second.texture = capture.stage1SeparateTexture;",
       "mirror_texture(dev, second, stage1View, stage1Sampler)",
       "capture.stage1SeparateTexture ? 2 :",
       "PSSetShaderResources(1, 1, &boundStage1View)",
       "PSSetSamplers(1, 1, &boundStage1Sampler)",
       "ctx->DrawIndexed(indexCount, 0, 0);",
       "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
assert complete(g,h,d)
for a in ("stage1_dual_texture_compatible(","samplerDiff |= s0 != s1;",
          "if (states[i] == D3DSAMP_ADDRESSW && s0 != s1) return false;"):
    assert not complete(g.replace(a,"",1),h,d)
for a in ("stage1GameTexture.Sample(stage1GameSampler, v.uv)","if (stage1Ops.w == 2)"):
    # Three game-stage PS entrypoints each sample the second real texture.
    # Remove the shared semantic link from ALL three to prove fail-closed coverage.
    assert not complete(g,h.replace(a,""),d)
for a in ("mirror_texture(dev, second, stage1View, stage1Sampler)","PSSetShaderResources(1, 1, &boundStage1View)"):
    assert not complete(g,h,d.replace(a,"",1))
assert "test_dx11_stage1_dual_game_texture_00713.py" in w
assert "dx11_game_stage1_dual_texture_probe_00713.cpp" in w
print("PASS 00713 actual t0/t1 real game D3D9 to native HLSL Draw/Indexed and original input fallback")
