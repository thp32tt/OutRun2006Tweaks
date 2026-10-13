#!/usr/bin/env python3
"""00661 destructive contracts: 16-bit X RGB game texture -> guarded native Draw."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HEADER = ROOT / "src/vr/d3d11/packed_texture_16bit.hpp"
PROBE = ROOT / "tools/dx11_game_xrgb16_probe.cpp"

def connected(src: str, decoder: str) -> bool:
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = src.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
        admit = mirror.split("const bool packed16 =", 1)[1].split("const bool luminance", 1)[0]
        select = mirror.split("const auto packing =", 1)[1].split("for (UINT y", 1)[0]
    except IndexError:
        return False
    return (all(s in admit for s in (
            "base.Format == D3DFMT_X1R5G5B5 ||",
            "base.Format == D3DFMT_X4R4G4B4;",
        )) and all(s in select for s in (
            "base.Format == D3DFMT_X1R5G5B5 ?",
            "packed_texture16::Layout::xrgb1555 :",
            "packed_texture16::Layout::xrgb4444;",
        )) and all(s in mirror for s in (
            "if (capture.srgbTexture && packed16) return false;",
            "if (base.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;",
            "const UINT sourceTexelBytes = packed16 ? 2u :",
            "const UINT uploadPitch = ((packed16 || luminance) || rgb24",
            "desc.Width * 4u : rowBytes;",
            "static_cast<UINT>(lock.Pitch) >= rowBytes",
            "packed_texture16::unpack_row(source, destination, desc.Width, packing)",
            "initial[level].SysMemPitch = pitches[level];",
            "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
        )) and all(s in decoder for s in (
            "case Layout::xrgb1555:",
            "case Layout::xrgb4444:",
            "expand5((value >> 10u) & 31u), 255u",
            "expand4((value >> 8u) & 15u), 255u",
            "unpack_row_typed<Layout::xrgb1555>(source, bgra, width);",
            "unpack_row_typed<Layout::xrgb4444>(source, bgra, width);",
        )) and all(s in draw for s in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )))

def main() -> None:
    src, decoder = BRIDGE.read_text(encoding="utf-8"), HEADER.read_text(encoding="utf-8")
    assert connected(src, decoder), "X1/X4 RGB source->BGRA8 mip SRV->game native Draw disconnected"
    probe = PROBE.read_text(encoding="utf-8")
    assert all(s in probe for s in (
        "Layout::xrgb1555", "Layout::xrgb4444", "0xfc00u", "0xff00u",
        "Layout::argb1555", "Layout::argb4444",
    )), "positive/negative reserved-alpha CPU probe missing"
    src_mutations = (
        ("base.Format == D3DFMT_X1R5G5B5 ||", "base.Format == D3DFMT_A1R5G5B5 ||"),
        ("base.Format == D3DFMT_X4R4G4B4;", "base.Format == D3DFMT_A4R4G4B4;"),
        ("base.Format == D3DFMT_X1R5G5B5 ?", "base.Format == D3DFMT_A1R5G5B5 ?"),
        ("packed_texture16::Layout::xrgb1555 :", "packed_texture16::Layout::argb1555 :"),
        ("packed_texture16::Layout::xrgb4444;", "packed_texture16::Layout::argb4444;"),
        ("if (capture.srgbTexture && packed16) return false;", "if (false) return false;"),
        ("static_cast<UINT>(lock.Pitch) >= rowBytes", "false"),
        ("packed_texture16::unpack_row(source, destination, desc.Width, packing)", "/* bypass */;"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->PSSetShaderResources(0, 1, &boundView);", "ctx->PSSetShaderResources(0, 0, &boundView);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
    )
    decoder_mutations = (
        ("case Layout::xrgb1555:", "case Layout::bad1555:"),
        ("case Layout::xrgb4444:", "case Layout::bad4444:"),
        ("expand5((value >> 10u) & 31u), 255u", "expand5((value >> 10u) & 31u), 0u"),
        ("expand4((value >> 8u) & 15u), 255u", "expand4((value >> 8u) & 15u), 0u"),
        ("unpack_row_typed<Layout::xrgb1555>(source, bgra, width);",
         "unpack_row_typed<Layout::argb1555>(source, bgra, width);"),
        ("unpack_row_typed<Layout::xrgb4444>(source, bgra, width);",
         "unpack_row_typed<Layout::argb4444>(source, bgra, width);"),
    )
    for old, mutation in src_mutations:
        assert old in src, old
        if old == "base.Format == D3DFMT_X1R5G5B5 ?":
            # 00692's earlier DEFAULT-RT admission checks the same D3D9
            # format. Mutate the LAST occurrence: this regression owns the
            # original texture packing selector inside the mip-copy loop.
            prefix, match, suffix = src.rpartition(old)
            mutant = prefix + mutation + suffix if match else src
        else:
            mutant = src.replace(old, mutation, 1)
        assert not connected(mutant, decoder), old
    for old, mutation in decoder_mutations:
        assert old in decoder and not connected(src, decoder.replace(old, mutation, 1)), old
    print(f"00661 PASS: {len(src_mutations)+len(decoder_mutations)} X1/X4 RGB destructive live Draw mutations; HMD UNTESTED")

if __name__ == "__main__":
    main()
