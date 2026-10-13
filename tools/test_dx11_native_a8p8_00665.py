#!/usr/bin/env python3
"""00665 live D3D9 A8P8 palette/alpha mips -> BGRA8 -> native Draw links."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HEADER = ROOT / "src/vr/d3d11/live_game_a8p8_texture.hpp"
PROBE = ROOT / "tools/dx11_game_a8p8_probe.cpp"

def linked(src, hdr):
    try:
        mirror = src.split("bool mirror_texture(",1)[1].split("bool submit(",1)[0]
        draw = src.split("bool submit(",1)[1].split("void before_game_present(",1)[0]
    except IndexError:
        return False
    return all(x in src for x in ('#include "live_game_a8p8_texture.hpp"',)) and all(
        x in mirror for x in (
            "const bool a8p8 = base.Format == D3DFMT_A8P8;",
            "if (capture.srgbTexture && a8p8) return false;",
            "if (base.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;",
            "else if (a8p8) {",
            "nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;",
            "capture.texture->GetDevice(paletteDevice.GetAddressOf())",
            "paletteDevice->GetCurrentTexturePalette(&paletteNumber)",
            "paletteDevice->GetPaletteEntries(paletteNumber, entries.data())",
            "activePalette[i] = {entries[i].peRed, entries[i].peGreen,",
            "a8p8 ? a8p8_texture::source_bytes_per_texel() :",
            "const UINT a8p8UploadPitch = a8p8 ? desc.Width * 4u : uploadPitch;",
            "if (a8p8) pixels.resize(static_cast<std::size_t>(a8p8UploadPitch) * rows);",
            "static_cast<std::size_t>(uploadPitch) * rows",
            "static_cast<std::size_t>(y) * uploadPitch",
            "pitches[level] = a8p8UploadPitch;",
            "static_cast<UINT>(lock.Pitch) >= rowBytes",
            "else if (a8p8)\n                    a8p8_texture::unpack_row(source, destination, desc.Width,",
            "activePalette.data());",
            "initial[level].SysMemPitch = pitches[level];",
            "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
            "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
        )
    ) and all(x in draw for x in (
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->PSSetShaderResources(0, 1, &boundView);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )) and all(x in hdr for x in (
        "source_bytes_per_texel() noexcept { return 2u; }",
        "const Rgb& color = palette[source[in]];",
        "bgra[out] = color.blue;",
        "bgra[out + 1u] = color.green;",
        "bgra[out + 2u] = color.red;",
        "bgra[out + 3u] = source[in + 1u];",
    ))

def main():
    src, hdr, probe = BRIDGE.read_text(), HEADER.read_text(), PROBE.read_text()
    assert linked(src,hdr), "A8P8 live native game Draw disconnected"
    assert all(x in probe for x in ("row*6u","row*8u","palette[255]","mip.data()",
                                   "std::array<std::uint8_t,4>{99,0,255,51}"))
    changes = (
        ('#include "live_game_a8p8_texture.hpp"', '#include "live_game_rg16_texture.hpp"'),
        ("const bool a8p8 = base.Format == D3DFMT_A8P8;", "const bool a8p8 = false;"),
        ("if (capture.srgbTexture && a8p8) return false;", "if (false && a8p8) return false;"),
        ("else if (a8p8) {", "else if (rg16) {"),
        ("capture.texture->GetDevice(paletteDevice.GetAddressOf())", "false"),
        ("paletteDevice->GetCurrentTexturePalette(&paletteNumber)", "false"),
        ("paletteDevice->GetPaletteEntries(paletteNumber, entries.data())", "false"),
        ("a8p8 ? a8p8_texture::source_bytes_per_texel() :", "4u :"),
        ("const UINT a8p8UploadPitch = a8p8 ? desc.Width * 4u : uploadPitch;",
         "const UINT a8p8UploadPitch = uploadPitch;"),
        ("pitches[level] = a8p8UploadPitch;", "pitches[level] = uploadPitch;"),
        ("activePalette.data());", "nullptr);"),
        ("static_cast<UINT>(lock.Pitch) >= rowBytes", "false"),
        ("initial[level].SysMemPitch = pitches[level];", "initial[level].SysMemPitch = 0;"),
        ("dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())", "false"),
        ("dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())", "false"),
        ("ctx->PSSetShaderResources(0, 1, &boundView);", "ctx->PSSetShaderResources(0, 0, &boundView);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    )
    head_changes = (
        ("const Rgb& color = palette[source[in]];", "const Rgb& color = palette[0];"),
        ("bgra[out] = color.blue;", "bgra[out] = color.red;"),
        ("bgra[out + 1u] = color.green;", "bgra[out + 1u] = color.red;"),
        ("bgra[out + 2u] = color.red;", "bgra[out + 2u] = color.blue;"),
        ("bgra[out + 3u] = source[in + 1u];", "bgra[out + 3u] = 255u;"),
        ("source_bytes_per_texel() noexcept { return 2u; }",
         "source_bytes_per_texel() noexcept { return 4u; }"),
    )
    for old,bad in changes:
        assert old in src and not linked(src.replace(old,bad,1),hdr),old
    for old,bad in head_changes:
        assert old in hdr and not linked(src,hdr.replace(old,bad,1)),old
    print(f"00665 PASS: {len(changes)+len(head_changes)} destructive native Draw/palette links; HMD UNTESTED")
if __name__ == "__main__":
    main()
