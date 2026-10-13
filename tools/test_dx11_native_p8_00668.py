#!/usr/bin/env python3
"""00668 live game P8 palette/caps/alpha + mip -> BGRA8 native DX11 Draw."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HEADER = ROOT / "src/vr/d3d11/live_game_p8_texture.hpp"
PROBE = ROOT / "tools/dx11_game_p8_probe.cpp"

def connected(src, hdr):
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = src.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    return '#include "live_game_p8_texture.hpp"' in src and all(s in mirror for s in (
        "const bool p8 = base.Format == D3DFMT_P8;",
        "if (capture.srgbTexture && p8) return false;",
        "if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
        "else if (p8) {",
        "nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;",
        "if (a8p8 || p8) {",
        "paletteDevice->GetCurrentTexturePalette(&paletteNumber)",
        "paletteDevice->GetPaletteEntries(paletteNumber, entries.data())",
        "paletteDevice->GetDeviceCaps(&caps)",
        "(caps.TextureCaps & D3DPTEXTURECAPS_ALPHAPALETTE) != 0u",
        "alphaPalette ? entries[i].peFlags : 0xffu",
        "p8 ? p8_texture::source_bytes_per_texel() :",
        "|| extendedLuma || rgb332 || p8 ?",
        "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
        "else if (p8)\n                    p8_texture::unpack_row(source, destination, desc.Width,",
        "p8Palette.data());",
        "initial[level].SysMemPitch = pitches[level];",
        "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
        "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
    )) and all(s in draw for s in (
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->PSSetShaderResources(0, 1, &boundView);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )) and all(s in hdr for s in (
        "source_bytes_per_texel() noexcept { return 1u; }",
        "const Rgba& color = palette[source[x]];",
        "bgra[out] = color.blue;",
        "bgra[out + 1u] = color.green;",
        "bgra[out + 2u] = color.red;",
        "bgra[out + 3u] = color.alpha;",
    ))

def main():
    src, hdr, cpp = SOURCE.read_text(), HEADER.read_text(), PROBE.read_text()
    assert connected(src, hdr), "P8 palette/caps/native game Draw path disconnected"
    assert all(s in cpp for s in ("row * 6u", "row * 14u", "mip.data()",
                                 "for (auto& entry : palette) entry.alpha = 255u;"))
    mutations = (
        ('#include "live_game_p8_texture.hpp"', '#include "live_game_rg16_texture.hpp"'),
        ("const bool p8 = base.Format == D3DFMT_P8;", "const bool p8 = false;"),
        ("if (capture.srgbTexture && p8) return false;", "if (false && p8) return false;"),
        ("else if (p8) {", "else if (rg16) {"),
        ("if (a8p8 || p8) {", "if (a8p8) {"),
        ("paletteDevice->GetCurrentTexturePalette(&paletteNumber)", "false"),
        ("paletteDevice->GetPaletteEntries(paletteNumber, entries.data())", "false"),
        ("paletteDevice->GetDeviceCaps(&caps)", "false"),
        ("(caps.TextureCaps & D3DPTEXTURECAPS_ALPHAPALETTE) != 0u", "false"),
        ("alphaPalette ? entries[i].peFlags : 0xffu", "0xffu"),
        ("p8 ? p8_texture::source_bytes_per_texel() :", "p8 ? 4u :"),
        ("|| extendedLuma || rgb332 || p8 ?", "|| extendedLuma || rgb332 ?"),
        ("else if (p8)\n                    p8_texture::unpack_row(source, destination, desc.Width,",
         "else if (p8)\n                    std::memcpy(destination, source, rowBytes);"),
        ("p8Palette.data());", "nullptr);"),
        ("initial[level].SysMemPitch = pitches[level];", "initial[level].SysMemPitch = 0u;"),
        ("ctx->PSSetShaderResources(0, 1, &boundView);", "ctx->PSSetShaderResources(0, 0, &boundView);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    )
    head_mutations = (
        ("source_bytes_per_texel() noexcept { return 1u; }",
         "source_bytes_per_texel() noexcept { return 4u; }"),
        ("const Rgba& color = palette[source[x]];", "const Rgba& color = palette[0];"),
        ("bgra[out] = color.blue;", "bgra[out] = color.red;"),
        ("bgra[out + 1u] = color.green;", "bgra[out + 1u] = color.red;"),
        ("bgra[out + 2u] = color.red;", "bgra[out + 2u] = color.blue;"),
        ("bgra[out + 3u] = color.alpha;", "bgra[out + 3u] = 255u;"),
    )
    for old, bad in mutations:
        assert old in src and not connected(src.replace(old, bad, 1), hdr), old
    for old, bad in head_mutations:
        assert old in hdr and not connected(src, hdr.replace(old, bad, 1)), old
    print(f"00668 PASS: {len(mutations) + len(head_mutations)} destructive P8/native Draw checks; HMD UNTESTED")

if __name__ == "__main__":
    main()
