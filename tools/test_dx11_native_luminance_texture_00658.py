#!/usr/bin/env python3
"""00658: real game D3D9 A8/L8/A8L8 pixels -> native D3D11 SRV -> Draw.

CPU pixel tests are compiled in dx11-fast-structural. This checks that the
production bridge calls the decoder and preserves unsupported sRGB fallback.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"


def connected(source: str) -> bool:
    try:
        mirror = source.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        submit = source.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    return (
        '#include "live_game_luminance_texture.hpp"' in source
        and "const bool luminance = base.Format == D3DFMT_A8 ||" in mirror
        and "base.Format == D3DFMT_L8 ||" in mirror
        and "base.Format == D3DFMT_A8L8;" in mirror
        and all(s in mirror for s in (
            "if (capture.srgbTexture && luminance) return false;",
            "base.Format == D3DFMT_X8R8G8B8 || packed16 || luminance",
            "luminance_texture::Layout::alpha8 :",
            "luminance_texture::Layout::luminance8",
            "luminance_texture::Layout::alpha8_luminance8",
            "luminance_texture::source_bytes_per_texel(luminanceLayout)",
            "desc.Width * sourceTexelBytes",
            "(packed16 || luminance)",
            "luminance_texture::unpack_row(source, destination, desc.Width, luminanceLayout)",
            "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
            "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
        ))
        and all(s in submit for s in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "ctx->PSSetSamplers(0, 1, &boundSampler);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        ))
    )


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert connected(source), "game alpha/luminance upload and draw path missing"
    mutations = (
        ('#include "live_game_luminance_texture.hpp"', '#include "packed_texture_16bit.hpp"'),
        ("base.Format == D3DFMT_A8 ||", "base.Format == D3DFMT_X8R8G8B8 ||"),
        ("base.Format == D3DFMT_L8 ||", "base.Format == D3DFMT_X8R8G8B8 ||"),
        ("base.Format == D3DFMT_A8L8;", "base.Format == D3DFMT_X8R8G8B8;"),
        ("if (capture.srgbTexture && luminance) return false;", "if (false && luminance) return false;"),
        ("base.Format == D3DFMT_X8R8G8B8 || packed16 || luminance", "base.Format == D3DFMT_X8R8G8B8 || packed16"),
        ("luminance_texture::Layout::alpha8", "luminance_texture::Layout::luminance8"),
        ("luminance_texture::source_bytes_per_texel(luminanceLayout)", "4u"),
        ("desc.Width * sourceTexelBytes", "desc.Width * 4u"),
        ("(packed16 || luminance)", "(packed16)"),
        ("luminance_texture::unpack_row(source, destination, desc.Width, luminanceLayout)", "std::memcpy(destination, source, rowBytes)"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
    )
    for old, bad in mutations:
        assert old in source, old
        assert not connected(source.replace(old, bad, 1)), "destructive mutation survived: " + old
    print(f"00658 PASS: {len(mutations)} destructive render-link mutations; exact build and HMD separately gated")


if __name__ == "__main__":
    main()
