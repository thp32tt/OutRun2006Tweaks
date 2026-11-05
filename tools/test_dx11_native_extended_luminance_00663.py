#!/usr/bin/env python3
"""00663: destructive game A4L4/L16 mips -> BGRA8 SRV -> native Draw contracts."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HEADER = ROOT / "src/vr/d3d11/live_game_extended_luminance_texture.hpp"
PROBE = ROOT / "tools/dx11_game_extended_luminance_probe.cpp"


def connected(src, hdr):
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = src.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    return ('#include "live_game_extended_luminance_texture.hpp"' in src
        and all(s in mirror for s in (
            "const bool extendedLuma = base.Format == D3DFMT_A4L4 ||",
            "base.Format == D3DFMT_L16;",
            "if (capture.srgbTexture && extendedLuma) return false;",
            "|| tenBit || extendedLuma) {",
            "extended_luminance_texture::Layout::luminance16 :",
            "extended_luminance_texture::Layout::alpha4_luminance4;",
            "extendedLuma ? extended_luminance_texture::source_bytes_per_texel(extendedLumaLayout) :",
            "|| rgbaSwizzle) || extendedLuma || rgb332 || p8 ?",
            "desc.Width * sourceTexelBytes",
            "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
            "else if (extendedLuma)",
            "extended_luminance_texture::unpack_row(source, destination, desc.Width, extendedLumaLayout);",
            "initial[level].SysMemPitch = pitches[level];",
            "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
            "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
            "if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
        )) and all(s in draw for s in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"
        )) and all(s in hdr for s in (
            "source[x] & 0x0fu", "source[x] >> 4u",
            "value * 17u", "(value * 255u + 32767u) / 65535u",
            "source[offset + 1u]) << 8u", "bgra[offset + 3u] = alpha;"
        )))


def main():
    src, hdr = SOURCE.read_text(), HEADER.read_text()
    assert connected(src, hdr), "live D3D9 A4L4/L16 mip-to-native Draw disconnected"
    probe = PROBE.read_text()
    assert all(s in probe for s in (
        "static_assert", "Layout::alpha4_luminance4", "Layout::luminance16",
        "0x87, 0x38", "0x00,0x80", "1u", "0u")), "CPU pixel/mip probe incomplete"
    mutants = (
        ('#include "live_game_extended_luminance_texture.hpp"', '#include "live_game_rgba_texture.hpp"'),
        ("const bool extendedLuma = base.Format == D3DFMT_A4L4 ||", "const bool extendedLuma = false ||"),
        ("base.Format == D3DFMT_L16;", "base.Format == D3DFMT_R8G8B8;"),
        ("if (capture.srgbTexture && extendedLuma) return false;", "if (false && extendedLuma) return false;"),
        ("|| tenBit || extendedLuma) {", "|| tenBit) {"),
        ("extended_luminance_texture::Layout::luminance16 :", "extended_luminance_texture::Layout::alpha4_luminance4 :"),
        ("extended_luminance_texture::Layout::alpha4_luminance4;", "extended_luminance_texture::Layout::luminance16;"),
        ("extendedLuma ? extended_luminance_texture::source_bytes_per_texel(extendedLumaLayout) :", "extendedLuma ? 4u :"),
        ("|| rgbaSwizzle) || extendedLuma || rgb332 || p8 ?", "|| rgbaSwizzle) || rgb332 || p8 ?"),
        ("dynamic_texture::readable_pitch(lock.Pitch, rowBytes)", "false"),
        ("else if (extendedLuma)", "else if (false)"),
        ("extended_luminance_texture::unpack_row(source, destination, desc.Width, extendedLumaLayout);", "std::memcpy(destination, source, rowBytes);"),
        ("initial[level].SysMemPitch = pitches[level];", "initial[level].SysMemPitch = 0;"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->PSSetShaderResources(0, 1, &boundView);", "ctx->PSSetShaderResources(0, 0, &boundView);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
    )
    header_mutants = (
        ("source[x] & 0x0fu", "source[x] & 0xf0u"),
        ("source[x] >> 4u", "source[x] >> 2u"),
        ("value * 17u", "value * 16u"),
        ("(value * 255u + 32767u) / 65535u", "(value * 255u) / 65535u"),
        ("source[offset + 1u]) << 8u", "source[offset + 1u]) << 4u"),
        ("bgra[offset + 3u] = alpha;", "bgra[offset + 3u] = 0u;"),
    )
    for original, broken in mutants:
        assert original in src and not connected(src.replace(original, broken, 1), hdr), original
    for original, broken in header_mutants:
        assert original in hdr and not connected(src, hdr.replace(original, broken, 1)), original
    print(f"00663 PASS: {len(mutants)+len(header_mutants)} destructive native Draw links; HMD UNTESTED")


if __name__ == "__main__":
    main()
