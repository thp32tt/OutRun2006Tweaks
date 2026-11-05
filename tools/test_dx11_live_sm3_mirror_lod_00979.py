#!/usr/bin/env python3
"""00979: live SM3 VS/PS shared managed-texture SetLOD receipt is exact."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HELPER = ROOT / "src/vr/d3d11/live_game_draw_mirror_cache.hpp"
CPP = ROOT / "tools/dx11_live_sm3_volume_00975.cpp"


def connected(source: str, helper: str, test: str) -> bool:
    # Multiple game shader slots must reuse the exact image generation and
    # independently apply their own D3D9 sampler. A hard-coded one-level
    # receipt worked for SetLOD(0) but poisoned SetLOD(n>0) DrawIndexed.
    begin = source.split("const auto mirrorLiveSampler =", 1)
    if len(begin) != 2:
        return False
    body = begin[1].split("std::array<ComPtr<ID3D11ShaderResourceView>,4>", 1)
    if len(body) != 2:
        return False
    shader = body[0]
    return all(p in shader for p in [
        "captured.cubeTexture->GetLevelCount()",
        "captured.volumeTexture->GetLevelCount()",
        "captured.texture->GetLevelCount()",
        "captured.cubeTexture->GetLOD()",
        "captured.volumeTexture->GetLOD()",
        "captured.texture->GetLOD()",
        "draw_mirror_cache::mirrored_source_levels(",
        "if (!mirrorLevels) return false;",
        "draw_mirror_cache::cached_sampler_compatible(",
        "previous.levels, sourceLevels, chain, sourceLod,",
        "!create_game_sampler(device, captured, previous.levels, sampler)",
        "drawMirrors[drawMirrorCount++] = {key, mirrorLevels, view};",
        "mirror_texture(device, captured, view, sampler)"
    ]) and all(p in helper for p in [
        "live_game_mip_lod::captured_levels(sourceLevels, mipChain, sourceLod)",
        "cachedLevels == expected",
        "live_game_mip_lod::select(cachedLevels, mipChain, sourceLod, maxMipLevel).valid"
    ]) and all(p in test for p in [
        "cached_sampler_compatible(4u, 6u, false, 3u, 0u)",
        "!cached_sampler_compatible(1u, 6u, false, 3u, 0u)",
        "!cached_sampler_compatible(4u, 6u, false, 3u, 1u)"
    ]) and "draw_mirror_cache::mirrored_source_levels(\n                sourceLevels" in source


def main() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    test = CPP.read_text(encoding="utf-8")
    assert connected(source, helper, test), "live game SM3 cached view SetLOD path disconnected"
    mutations = [
        (source, helper, test,
         "drawMirrors[drawMirrorCount++] = {key, mirrorLevels, view};",
         "drawMirrors[drawMirrorCount++] = {key, 1u, view};", "src"),
        (source, helper, test,
         "previous.levels, sourceLevels, chain, sourceLod,",
         "previous.levels, 1u, chain, sourceLod,", "src"),
        (source, helper, test,
         "draw_mirror_cache::cached_sampler_compatible(",
         "false /* removed cached_sampler_compatible */", "src"),
        (source, helper, test,
         "draw_mirror_cache::mirrored_source_levels(",
         "1u /* removed mirrored_source_levels */", "src"),
        (source, helper, test,
         "draw_mirror_cache::mirrored_source_levels(\n                sourceLevels",
         "1u /* removed stage1 source LOD */", "src"),
        (source, helper, test,
         "captured.volumeTexture->GetLOD()",
         "0u /* lost volume SetLOD */", "src"),
        (source, helper, test,
         "captured.cubeTexture->GetLOD()",
         "0u /* lost cube SetLOD */", "src"),
        (source, helper, test,
         "captured.texture->GetLOD()",
         "0u /* lost 2D SetLOD */", "src"),
        (source, helper, test,
         "cachedLevels == expected",
         "cachedLevels == 1u", "hdr"),
        (source, helper, test,
         "live_game_mip_lod::captured_levels(sourceLevels, mipChain, sourceLod)",
         "1u", "hdr"),
        (source, helper, test,
         "!cached_sampler_compatible(1u, 6u, false, 3u, 0u)",
         "cached_sampler_compatible(1u, 6u, false, 3u, 0u)", "cpp"),
    ]
    for s, h, t, old, new, kind in mutations:
        base = {"src": s, "hdr": h, "cpp": t}[kind]
        assert old in base, old
        replaced = base.replace(old, new, 1)
        parts = {"src": s, "hdr": h, "cpp": t}
        parts[kind] = replaced
        assert not connected(parts["src"], parts["hdr"], parts["cpp"]), old
    print("00979 PASS: SM3 VS/PS 2D/cube/volume SetLOD shared SRV; 11 negative mutations; runtime UNTESTED")


if __name__ == "__main__":
    main()
