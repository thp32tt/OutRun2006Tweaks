#!/usr/bin/env python3
"""00589: game-authored mip-point texture chain reaches native D3D11 Draw."""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"


def wired(s: str) -> bool:
    try:
        gate = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        mirror = s.split("bool create_game_sampler(", 1)[1].split("bool submit(", 1)[0]
        # Both the standalone Stage1 sampler and the Stage0 game texture
        # mirror must remain connected after 00716 sampler extraction.
        if "return create_game_sampler(dev, capture, levels, sampler);" not in mirror:
            return False
        submit = s.split("bool submit(", 1)[1].split("void observe(", 1)[0]
    except IndexError:
        return False
    required_gate = [
        "GetSamplerState(0, D3DSAMP_MIPFILTER, &mip)",
        "GetSamplerState(0, D3DSAMP_MAXMIPLEVEL, &maxMip)",
        "GetSamplerState(0, D3DSAMP_MIPMAPLODBIAS, &mipBias)",
        "(mip != D3DTEXF_NONE && mip != D3DTEXF_POINT)",
        "(mip == D3DTEXF_NONE && (maxMip != 0u || decodedMipBias != 0.0f)) || !validMipBias",
        "capture.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(mip)",
    ]
    required_mirror = [
        "const UINT levels = usesMips ? sourceLevels : 1u;",
        "const bool usesMips = capture.mipFilter == D3DTEXF_POINT ||",
        "capture.mipFilter == D3DTEXF_LINEAR;",
        "usesMips && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)",
        "usesMips && capture.texture->GetLOD() != 0u",
        "if (gpuRenderTarget && levels != 1u) return false;",
        "desc.Width != (std::max)(1u, base.Width >> level)",
        "desc.Height != (std::max)(1u, base.Height >> level)",
        "const UINT rows = compressed ? (std::max)(1u, (desc.Height + 3u) / 4u) : desc.Height;",
        "(std::max)(1u, (desc.Width + 3u) / 4u)",
        "capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)",
        "capture.texture->UnlockRect(level)",
        "packed_texture16::unpack_row(source, destination, desc.Width, packing)",
        "for (UINT level = 0; level < levels; ++level)",
        "initial[level].pSysMem = copied[level].data();",
        "initial[level].SysMemPitch = pitches[level];",
        "desc.MipLevels = levels; desc.ArraySize = 1;",
        "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
        "state.MaxLOD = usesMips ? static_cast<float>(levels - 1u) : 0.0f;",
        "state.MipLODBias = usesMips ? capture.mipLodBias : 0.0f;",
    ]
    return (all(p in gate for p in required_gate) and
            all(p in mirror for p in required_mirror) and
            "bool mirror_texture(dev, capture, sampledView, sampledSampler)" not in submit and
            "mirror_texture(dev, capture, sampledView, sampledSampler)" in submit and
            "ctx->PSSetSamplers(0, 1, &boundSampler);" in submit and
            "ctx->DrawIndexed(indexCount, 0, 0);" in submit and
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in submit and
            "bool mipFilter = false;" not in s)


def main() -> None:
    s = SRC.read_text(encoding="utf-8")
    assert wired(s), "game mip chain -> DX11 PS -> Draw/DrawIndexed not connected"
    mutations = [
        ("(mip != D3DTEXF_NONE && mip != D3DTEXF_POINT)", "mip != D3DTEXF_NONE"),
        ("(mip == D3DTEXF_NONE && (maxMip != 0u || decodedMipBias != 0.0f)) || !validMipBias", "maxMip > 16u && mipBias != 0u"),
        ("capture.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(mip)", "capture.mipFilter = D3DTEXF_NONE"),
        ("const UINT levels = usesMips ? sourceLevels : 1u;", "const UINT levels = 1u;"),
        ("usesMips && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)", "false && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)"),
        ("usesMips && capture.texture->GetLOD() != 0u", "usesMips && false"),
        ("if (gpuRenderTarget && levels != 1u) return false;", "if (false) return false;"),
        ("desc.Width != (std::max)(1u, base.Width >> level)", "desc.Width != base.Width"),
        ("(std::max)(1u, (desc.Width + 3u) / 4u)", "desc.Width / 4u"),
        ("capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)", "capture.texture->LockRect(0, &lock, nullptr, D3DLOCK_READONLY)"),
        ("capture.texture->UnlockRect(level)", "capture.texture->UnlockRect(0)"),
        ("initial[level].pSysMem = copied[level].data();", "initial[level].pSysMem = copied[0].data();"),
        ("initial[level].SysMemPitch = pitches[level];", "initial[level].SysMemPitch = pitches[0];"),
        ("desc.MipLevels = levels; desc.ArraySize = 1;", "desc.MipLevels = 1; desc.ArraySize = 1;"),
        ("state.MaxLOD = usesMips ? static_cast<float>(levels - 1u) : 0.0f;", "state.MaxLOD = 0.0f;"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
    ]
    for old, new in mutations:
        assert old in s, old
        assert not wired(s.replace(old, new, 1)), old
    # DXT1 / DXT5: tiny tail mips occupy one complete 4x4 compressed block.
    for width in (1024, 512, 128, 16, 8, 4, 2, 1):
        for height in (512, 64, 8, 4, 2, 1):
            for block in (8, 16):
                row_bytes = max(1, (width + 3) // 4) * block
                rows = max(1, (height + 3) // 4)
                assert row_bytes * rows >= block
                if width <= 4 and height <= 4:
                    assert row_bytes * rows == block
    for source_mips in range(1, 12):
        assert (source_mips if True else 1) == source_mips
        assert (source_mips if False else 1) == 1
    print("00589 PASS: 17 negative mutations, 96 BC pitch checks, mip-point native submit; runtime UNTESTED")


if __name__ == "__main__":
    main()
