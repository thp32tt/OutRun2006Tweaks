#!/usr/bin/env python3
"""Real SM3 game Draw binds one native SRV per cube/2D image and slot-local samplers."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
hdr=(root/"src/vr/d3d11/live_game_draw_mirror_cache.hpp").read_text()
wf=(root/".github/workflows/dx11-fast-structural.yml").read_text()
def integrated(x,h):
    try:
        start=x.index("const auto mirrorLiveSampler =")
        stop=x.index("std::array<ComPtr<ID3D11ShaderResourceView>,4> vertexViews",start)
        vs=x.index("!mirrorLiveSampler(capture,",stop)
        ps=x.index("!mirrorLiveSampler(capture, views[slot], samplers[slot])",vs)
        native=x.index("context->DrawIndexed(nativeIndexCount",ps)
        block=x[start:stop]
    except ValueError:
        return False
    return all((
        "(!captured.texture && !captured.cubeTexture)" in block,
        "(captured.texture && captured.cubeTexture)" in block,
        "captured.cubeTexture != nullptr" in block,
        "captured.cubeTexture.Get()" in block,
        "captured.texture.Get()" in block,
        "captured.srgbTexture, chain, cube" in block,
        "draw_mirror_cache::same_view(key, previous.key)" in block,
        "create_game_sampler(device, captured, previous.levels, sampler)" in block,
        "view = previous.view" in block,
        "mirror_texture(device, captured, view, sampler)" in block,
        "captured.cubeTexture->GetLevelCount()" in block,
        "drawMirrors[drawMirrorCount++] = {key, levels, view};" in block,
        "mirror_cube_texture(dev, capture, view, sampler)" in x,
        "create_game_sampler(dev, capture, uploadedLevels, sampler)" in x,
        start < vs < ps < native,
        "a.cube == b.cube" in h,
    ))
assert integrated(src,hdr)
for needle in ("captured.cubeTexture.Get()","captured.cubeTexture->GetLevelCount()",
               "create_game_sampler(device, captured, previous.levels, sampler)",
               "(!captured.texture && !captured.cubeTexture)",
               "(captured.texture && captured.cubeTexture)",
               "mirror_cube_texture(dev, capture, view, sampler)"):
    assert not integrated(src.replace(needle,"/* removed */",1),hdr),needle
assert not integrated(src,hdr.replace("a.cube == b.cube","true",1))
assert "dx11_live_game_draw_mirror_probe_00972.cpp" in wf
assert "test_dx11_live_game_draw_mirror_00972.py" in wf
print("PASS VS/PS cube+2D native SRV identity, independent samplers, D3D9 fallback")
