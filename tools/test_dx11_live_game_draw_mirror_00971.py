#!/usr/bin/env python3
"""Real shader-bound game Draw: dimension-correct VS/PS image alias and independent samplers."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
hdr=(root/"src/vr/d3d11/live_game_draw_mirror_cache.hpp").read_text()
wf=(root/".github/workflows/dx11-fast-structural.yml").read_text()
def integrated(x):
    try:
        start=x.index("const auto mirrorLiveSampler =")
        end=x.index("std::array<ComPtr<ID3D11ShaderResourceView>,4> vertexViews",start)
        block=x[start:end]
        v=x.index("!mirrorLiveSampler(capture,\n                               vertexViews[slot], vertexSamplers[slot])",end)
        p=x.index("!mirrorLiveSampler(capture, views[slot], samplers[slot])",v)
        draw=x.index("context->DrawIndexed(nativeIndexCount",p)
    except ValueError:
        return False
    return all((
        "std::array<DrawMirror, 20u> drawMirrors{}" in x,
        "draw_mirror_cache::same_view(key, previous.key)" in block,
        "create_game_sampler(device, captured, previous.levels, sampler)" in block,
        "view = previous.view" in block,
        "mirror_texture(device, captured, view, sampler)" in block,
        "captured.texture->GetLevelCount()" in block,
        "(static_cast<unsigned>(captured.texture != nullptr) +
             static_cast<unsigned>(captured.cubeTexture != nullptr) +
             static_cast<unsigned>(captured.volumeTexture != nullptr)) != 1u" in block,
        "drawMirrors[drawMirrorCount++] = {key, levels, view};" in block,
        start < v < p < draw,
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in x,
        "a.srgb == b.srgb" in hdr,
        "a.mipChain == b.mipChain" in hdr,
        "a.cube == b.cube" in hdr,
        "a.volume == b.volume" in hdr,
    ))
assert integrated(src)
for needle in ("draw_mirror_cache::same_view(key, previous.key)",
               "create_game_sampler(device, captured, previous.levels, sampler)",
               "view = previous.view",
               "(static_cast<unsigned>(captured.texture != nullptr) +
             static_cast<unsigned>(captured.cubeTexture != nullptr) +
             static_cast<unsigned>(captured.volumeTexture != nullptr)) != 1u",
               "!mirrorLiveSampler(capture, views[slot], samplers[slot])"):
    assert needle in src
    assert not integrated(src.replace(needle,"/* removed */",1)), needle
assert "dx11_live_game_draw_mirror_probe_00971.cpp" in wf
assert "test_dx11_live_game_draw_mirror_00971.py" in wf
print("PASS SM3 source-aware 2D view, independent VS/PS native samplers, original D3D9 fallback")
