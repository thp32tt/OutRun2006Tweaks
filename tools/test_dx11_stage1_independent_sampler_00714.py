#!/usr/bin/env python3
"""Independent real game stage-1 D3D9 sampler -> native t1/s1 Draw parity."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
c=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
h=(r/"src/vr/d3d11/live_game_stage1_dual_texture.hpp").read_text()
w=(r/".github/workflows/dx11-fast-structural.yml").read_text()
g=c.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
d=c.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
s=c.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
def integrated(g,d,s):
    return all(t in g for t in (
        "GetSamplerState(1, states[i], &s1)",
        "capture.stage1SamplerStates[i] = s1",
        "stage1_game_sampler_supported(",
        "capture.stage1IndependentSampler = samplerDiff",
        "tex1.Get() != tex.Get() || samplerDiff",
        "if (states[i] == D3DSAMP_ADDRESSW && s0 != s1) return false;")) and all(t in d for t in (
        "if (capture.stage1IndependentSampler)",
        "second.addressU = static_cast<D3DTEXTUREADDRESS>(ss[0])",
        "second.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(ss[5])",
        "second.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(ss[6])",
        "second.srgbTexture = ss[10] != FALSE",
        "std::memcpy(&second.mipLodBias, &ss[7]",
        "mirror_texture(dev, second, stage1View, stage1Sampler)",
        "PSSetSamplers(1, 1, &boundStage1Sampler)",
        "ctx->DrawIndexed(indexCount, 0, 0)",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0)")) and all(t in s for t in (
        "stage1GameTexture.Sample(stage1GameSampler, v.uvStage1)",
        "SamplerState stage1GameSampler : register(s1);"))
assert integrated(g,d,s)
for token in ("stage1_game_sampler_supported(", "tex1.Get() != tex.Get() || samplerDiff"):
    assert not integrated(g.replace(token,"",1),d,s)
for token in ("second.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(ss[5])",
              "second.srgbTexture = ss[10] != FALSE",
              "PSSetSamplers(1, 1, &boundStage1Sampler)"):
    assert not integrated(g,d.replace(token,"",1),s)
assert "stage1_game_sampler_supported(" in h
assert "test_dx11_stage1_independent_sampler_00714.py" in w
assert "dx11_game_stage1_sampler_probe_00714.cpp" in w
print("PASS 00714: live sampler1 snapshot, format/mip fallback, D3D11 t1/s1 Draw/Indexed")
