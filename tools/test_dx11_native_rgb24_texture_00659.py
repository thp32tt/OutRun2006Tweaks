#!/usr/bin/env python3
"""00659: game D3D9 BGR24 source -> native D3D11 Draw edge regression."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"

def connected(src):
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = src.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    return ('#include "live_game_rgb24_texture.hpp"' in src
        and all(s in mirror for s in (
            "const bool rgb24 = base.Format == D3DFMT_R8G8B8;",
            "base.Format == D3DFMT_X8R8G8B8 || packed16 || luminance || rgb24",
            "rgb24 ? rgb24_texture::source_bytes_per_texel() : 4u",
            "(packed16 || luminance) || rgb24",
            "desc.Width * sourceTexelBytes",
            "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
            "else if (rgb24)",
            "rgb24_texture::unpack_row(source, destination, desc.Width);",
            "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
            "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
            "if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
        ))
        and all(s in draw for s in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )))

def main():
    source = SOURCE.read_text(encoding="utf-8")
    assert connected(source), "24-bit live game texture -> D3D11 Draw link missing"
    mutants = (
        ('#include "live_game_rgb24_texture.hpp"', '#include "packed_texture_16bit.hpp"'),
        ("const bool rgb24 = base.Format == D3DFMT_R8G8B8;", "const bool rgb24 = false;"),
        ("base.Format == D3DFMT_X8R8G8B8 || packed16 || luminance || rgb24", "base.Format == D3DFMT_X8R8G8B8 || packed16 || luminance"),
        ("rgb24 ? rgb24_texture::source_bytes_per_texel() : 4u", "4u"),
        ("(packed16 || luminance) || rgb24", "(packed16 || luminance)"),
        ("dynamic_texture::readable_pitch(lock.Pitch, rowBytes)", "false"),
        ("else if (rgb24)", "else if (false)"),
        ("rgb24_texture::unpack_row(source, destination, desc.Width);", "std::memcpy(destination, source, rowBytes);"),
        ("if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;", "if (false) return false;"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
    )
    for old, bad in mutants:
        assert old in source, old
        assert not connected(source.replace(old,bad,1)), "destructive mutation survived: " + old
    print(f"00659 PASS: {len(mutants)} RGB24 native Draw mutations; HMD UNTESTED")

if __name__ == "__main__":
    main()
