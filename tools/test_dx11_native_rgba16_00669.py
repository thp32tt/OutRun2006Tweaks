#!/usr/bin/env python3
"""00669: live game A16B16G16R16 LockRect mips -> native RGBA16 SRV Draw."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HDR = ROOT / "src/vr/d3d11/live_game_rgba16_texture.hpp"
PROBE = ROOT / "tools/dx11_game_rgba16_probe.cpp"


def linked(src, header):
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = src.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    source_contract = (
        '#include "live_game_rgba16_texture.hpp"',
        "const bool rgba16 = base.Format == D3DFMT_A16B16G16R16;",
        "if (capture.srgbTexture && rgba16) return false;",
        "else if (rgba16) {",
        "nativeFormat = DXGI_FORMAT_R16G16B16A16_UNORM;",
        "rgba16 ? rgba16_texture::source_bytes_per_texel() :",
        "else if (rgba16)\n                    rgba16_texture::copy_row(source, destination, desc.Width);",
        "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
        "if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
        "initial[level].SysMemPitch = pitches[level];",
        "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
        "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
    )
    draw_contract = (
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->PSSetShaderResources(0, 1, &boundView);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )
    header_contract = (
        "return 8u;",
        "std::memcpy(destination, source,",
        "static_cast<std::size_t>(width) * source_bytes_per_texel()",
    )
    return (source_contract[0] in src and all(x in mirror for x in source_contract[1:])
            and all(x in draw for x in draw_contract)
            and all(x in header for x in header_contract))


def main():
    src, header, probe = SRC.read_text(), HDR.read_text(), PROBE.read_text()
    assert linked(src, header), "A16B16G16R16 source-to-native Draw path disconnected"
    assert all(x in probe for x in ("game.data()+20", "nativeMip != mip", "copy_row("))
    mutations = (
        ('#include "live_game_rgba16_texture.hpp"', '#include "live_game_rg16_texture.hpp"'),
        ("const bool rgba16 = base.Format == D3DFMT_A16B16G16R16;", "const bool rgba16 = false;"),
        ("if (capture.srgbTexture && rgba16) return false;", "if (false && rgba16) return false;"),
        ("nativeFormat = DXGI_FORMAT_R16G16B16A16_UNORM;", "nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;"),
        ("rgba16 ? rgba16_texture::source_bytes_per_texel() :", "rgba16 ? 4u :"),
        ("rgba16_texture::copy_row(source, destination, desc.Width);", "std::memcpy(destination, source, desc.Width * 4u);"),
        ("initial[level].SysMemPitch = pitches[level];", "initial[level].SysMemPitch = 0u;"),
        ("ctx->PSSetShaderResources(0, 1, &boundView);", "ctx->PSSetShaderResources(0, 0, &boundView);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    )
    header_mutations = (
        ("return 8u;", "return 4u;"),
        ("std::memcpy(destination, source,", "std::memset(destination, 0,"),
        ("static_cast<std::size_t>(width) * source_bytes_per_texel()", "width * 4u"),
    )
    for old, bad in mutations:
        assert old in src and not linked(src.replace(old, bad, 1), header), old
    for old, bad in header_mutations:
        assert old in header and not linked(src, header.replace(old, bad, 1)), old
    print(f"00669 PASS: {len(mutations)+len(header_mutations)} destructive native RGBA16 integration checks; HMD UNTESTED")


if __name__ == "__main__":
    main()
