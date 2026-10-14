#!/usr/bin/env python3
"""00716 live game Stage1 same-texture SRV reuse and independent sampler."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
helper = (root / "src/vr/d3d11/live_game_stage1_mirror_reuse.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
sampler = bridge.split("bool create_game_sampler(", 1)[1].split("bool mirror_texture(", 1)[0]
mirror = bridge.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
submit = bridge.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
shader = bridge.split('constexpr char kStage1FactorShader[] = R"(', 1)[1].split(')";', 1)[0]
def integrated(s, m, h, g, src):
    return all(k in s for k in (
        "const UINT mirroredLevels =", "stage1_game_mirror_reusable(",
        "capture.texture.Get() == second.texture.Get()",
        "capture.srgbTexture == second.srgbTexture",
        "capture.mipFilter != D3DTEXF_NONE",
        "second.mipFilter != D3DTEXF_NONE",
        "create_game_sampler(dev, second, mirroredLevels, stage1Sampler)",
        "stage1View = sampledView;",
        "else if (!mirror_texture(dev, second, stage1View, stage1Sampler))",
        "ctx->PSSetShaderResources(1, 1, &boundStage1View);",
        "ctx->PSSetSamplers(1, 1, &boundStage1Sampler);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )) and all(k in m for k in (
        "return create_game_sampler(dev, capture, levels, sampler);",
        "CreateTexture2D(&desc, initial.data()", "CreateShaderResourceView(texture.Get()",
    )) and all(k in h for k in (
        "D3D11_SAMPLER_DESC state{};", "capture.maxMipLevel >= levels",
        "CreateSamplerState(&state, sampler.GetAddressOf())",
    )) and all(k in g for k in (
        "sameSourceTexture && sameSrgbEncoding",
        "stage0UsesMips == stage1UsesMips && stage0NativeViewReady",
    )) and src.count("stage1GameTexture.Sample(stage1GameSampler, v.uvStage1)") == 3
assert integrated(submit, mirror, sampler, helper, shader)
for poison in ("stage1View = sampledView;", "capture.srgbTexture == second.srgbTexture",
               "second.mipFilter != D3DTEXF_NONE",
               "create_game_sampler(dev, second, mirroredLevels, stage1Sampler)",
               "else if (!mirror_texture(dev, second, stage1View, stage1Sampler))",
               "ctx->PSSetSamplers(1, 1, &boundStage1Sampler);"):
    assert not integrated(submit.replace(poison, "", 1), mirror, sampler, helper, shader)
assert not integrated(submit, mirror.replace(
    "return create_game_sampler(dev, capture, levels, sampler);", "", 1),
    sampler, helper, shader)
assert not integrated(submit, mirror, sampler,
    helper.replace("stage0UsesMips == stage1UsesMips", "true", 1), shader)
assert "test_dx11_stage1_mirror_reuse_00716.py" in workflow
assert "dx11_game_stage1_mirror_reuse_probe_00716.cpp" in workflow
print("PASS 00716: live D3D9 game Stage1 same-source native SRV reuse + independent sampler, fallback and Draw/Indexed")
