#!/usr/bin/env python3
"""00592: live game MAXMIPLEVEL reaches native Draw/DrawIndexed via D3D11 MinLOD."""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def connected(s: str) -> bool:
    try:
        gate = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        mirror = s.split("bool create_game_sampler(", 1)[1].split("bool submit(", 1)[0]
        # Both the standalone Stage1 sampler and the Stage0 game texture
        # mirror must remain connected after 00716 sampler extraction.
        if "return create_game_sampler(dev, capture, levels, sampler);" not in mirror:
            return False
        draw = s.split("bool submit(", 1)[1].split("void observe(", 1)[0]
        capture = s.split("struct TextureCapture {", 1)[1].split("struct OutputCapture {", 1)[0]
    except IndexError:
        return False
    g = (
        "GetSamplerState(0, D3DSAMP_MAXMIPLEVEL, &maxMip)",
        "GetSamplerState(0, D3DSAMP_MIPFILTER, &mip)",
        "GetSamplerState(0, D3DSAMP_MIPMAPLODBIAS, &mipBias)",
        "(mip == D3DTEXF_NONE && (maxMip != 0u || decodedMipBias != 0.0f)) || !validMipBias",
        "capture.maxMipLevel = maxMip;",
        "capture.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(mip)",
    )
    m = (
        "const UINT sourceLevels = capture.texture->GetLevelCount();",
        "const bool usesMips = capture.mipFilter == D3DTEXF_POINT ||",
        "capture.mipFilter == D3DTEXF_LINEAR;",
        "if (usesMips && capture.maxMipLevel >= sourceLevels) return false;",
        "const UINT levels = usesMips ? sourceLevels : 1u;",
        "if (usesMips && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)) return false;",
        "if (usesMips && capture.texture->GetLOD() != 0u) return false;",
        "capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)",
        "initial[level].pSysMem = copied[level].data();",
        "desc.MipLevels = levels; desc.ArraySize = 1;",
        "state.MinLOD = usesMips ? static_cast<float>(capture.maxMipLevel) : 0.0f;",
        "state.MaxLOD = usesMips ? static_cast<float>(levels - 1u) : 0.0f;",
        "dev->CreateSamplerState(&state, sampler.GetAddressOf())",
    )
    d = (
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->PSSetSamplers(0, 1, &boundSampler);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    return (all(x in s for x in ("return optedIn;", "void before_game_present("))
            and all(x in capture for x in ("DWORD maxMipLevel = 0u;",))
            and all(x in gate for x in g)
            and all(x in mirror for x in m)
            and all(x in draw for x in d))

def reference_min_lod(mip_filter: str, max_mip: int, levels: int) -> float | None:
    # The native opt-in path declines invalid requests instead of emitting a false sample.
    if levels < 1 or levels > 11 or max_mip < 0:
        return None
    if mip_filter == "none":
        return 0.0 if max_mip == 0 else None
    if mip_filter not in ("point", "linear") or max_mip >= levels:
        return None
    return float(max_mip)

def main() -> None:
    s = SRC.read_text(encoding="utf-8")
    assert connected(s), "game mip state -> CPU mip chain -> native sampler -> game Draw disconnected"
    mutations = [
        ("capture.maxMipLevel = maxMip;", "capture.maxMipLevel = 0u;"),
        ("DWORD maxMipLevel = 0u;", "DWORD maxMipLevel = ~0u;"),
        ("GetSamplerState(0, D3DSAMP_MAXMIPLEVEL, &maxMip)", "GetSamplerState(0, D3DSAMP_MAXMIPLEVEL, &mipBias)"),
        ("GetSamplerState(0, D3DSAMP_MIPFILTER, &mip)", "GetSamplerState(0, D3DSAMP_MIPFILTER, &mag)"),
        ("(mip == D3DTEXF_NONE && (maxMip != 0u || decodedMipBias != 0.0f)) || !validMipBias", "mipBias != 0u"),
        ("if (usesMips && capture.maxMipLevel >= sourceLevels) return false;", "if (false) return false;"),
        ("state.MinLOD = usesMips ? static_cast<float>(capture.maxMipLevel) : 0.0f;", "state.MinLOD = 0.0f;"),
        ("state.MaxLOD = usesMips ? static_cast<float>(levels - 1u) : 0.0f;", "state.MaxLOD = 0.0f;"),
        ("const UINT levels = usesMips ? sourceLevels : 1u;", "const UINT levels = 1u;"),
        ("capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)", "capture.texture->LockRect(0, &lock, nullptr, D3DLOCK_READONLY)"),
        ("initial[level].pSysMem = copied[level].data();", "initial[level].pSysMem = copied[0].data();"),
        ("if (usesMips && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)) return false;", "if (false) return false;"),
        ("if (usesMips && capture.texture->GetLOD() != 0u) return false;", "if (false) return false;"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    ]
    for before, after in mutations:
        assert before in s, before
        assert not connected(s.replace(before, after, 1)), f"undetected source mutation: {before}"
    cases = 0
    for levels in range(1, 12):
        for mode in ("none", "point", "linear", "aniso"):
            for max_mip in range(0, levels + 3):
                got = reference_min_lod(mode, max_mip, levels)
                valid = (max_mip == 0 if mode == "none" else
                         max_mip < levels if mode in ("point", "linear") else False)
                assert (got is not None) == valid
                if got is not None:
                    assert 0.0 <= got <= float(levels - 1)
                cases += 1
    assert reference_min_lod("linear", 3, 5) == 3.0
    assert reference_min_lod("point", 4, 5) == 4.0
    assert reference_min_lod("linear", 5, 5) is None
    assert reference_min_lod("none", 1, 5) is None
    print(f"00592 PASS: {cases} level/filter boundary cases, {len(mutations)} destructive source mutations; runtime UNTESTED")

if __name__ == "__main__":
    main()
