#!/usr/bin/env python3
"""00664 G16R16 game-authored mip rows -> BGRA8 -> native Draw contract."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HEADER = ROOT / "src/vr/d3d11/live_game_rg16_texture.hpp"
PROBE = ROOT / "tools/dx11_game_rg16_probe.cpp"

def connected(src, hdr):
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = src.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    return ('#include "live_game_rg16_texture.hpp"' in src
        and all(s in mirror for s in (
            "const bool rg16 = base.Format == D3DFMT_G16R16;",
            "if (capture.srgbTexture && rg16) return false;",
            "else if (rg16) {",
            "nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;",
            "else if (rg16)\n                    rg16_texture::unpack_row(source, destination, desc.Width);",
            "desc.Width * sourceTexelBytes",
            "static_cast<UINT>(lock.Pitch) >= rowBytes",
            "initial[level].SysMemPitch = pitches[level];",
            "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
            "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
            "if (base.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;",
        )) and all(s in draw for s in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )) and all(s in hdr for s in (
            "source[pos + 1u]) << 8u", "source[pos + 3u]) << 8u",
            "bgra[pos] = 0u;", "bgra[pos + 1u] = expand16(green);",
            "bgra[pos + 2u] = expand16(red);", "bgra[pos + 3u] = 255u;",
            "(value * 255u + 32767u) / 65535u",
        )))

def main():
    src, hdr = SOURCE.read_text(), HEADER.read_text()
    assert connected(src, hdr), "live G16R16 game native Draw chain not connected"
    probe = PROBE.read_text()
    assert all(s in probe for s in (
        "static_assert", "0xff,0xff,0x00,0x00",
        "0x00,0x80,0xff,0x7f", "y*10u", "1u", "0u",
        "std::array<std::uint8_t,4>{0,128,127,255}",
    )), "padded-row/mip CPU probe not connected"
    src_mutants = (
        ('#include "live_game_rg16_texture.hpp"', '#include "live_game_rgb24_texture.hpp"'),
        ("const bool rg16 = base.Format == D3DFMT_G16R16;", "const bool rg16 = false;"),
        ("if (capture.srgbTexture && rg16) return false;", "if (false && rg16) return false;"),
        ("else if (rg16) {", "else if (false) {"),
        ("rg16_texture::unpack_row(source, destination, desc.Width);", "std::memcpy(destination, source, rowBytes);"),
        ("static_cast<UINT>(lock.Pitch) >= rowBytes", "false"),
        ("initial[level].SysMemPitch = pitches[level];", "initial[level].SysMemPitch = 0;"),
        ("dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())", "false"),
        ("dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())", "false"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->PSSetShaderResources(0, 1, &boundView);", "ctx->PSSetShaderResources(0, 0, &boundView);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    )
    hdr_mutants = (
        ("source[pos + 1u]) << 8u", "source[pos + 1u]) << 4u"),
        ("source[pos + 3u]) << 8u", "source[pos + 3u]) << 4u"),
        ("bgra[pos] = 0u;", "bgra[pos] = 255u;"),
        ("bgra[pos + 1u] = expand16(green);", "bgra[pos + 1u] = expand16(red);"),
        ("bgra[pos + 2u] = expand16(red);", "bgra[pos + 2u] = expand16(green);"),
        ("bgra[pos + 3u] = 255u;", "bgra[pos + 3u] = 0u;"),
        ("(value * 255u + 32767u) / 65535u", "(value * 255u) / 65535u"),
    )
    for old, bad in src_mutants:
        assert old in src and not connected(src.replace(old, bad, 1), hdr), old
    for old, bad in hdr_mutants:
        assert old in hdr and not connected(src, hdr.replace(old, bad, 1)), old
    print(f"00664 PASS: {len(src_mutants)+len(hdr_mutants)} destructive game Draw links; HMD UNTESTED")

if __name__ == "__main__":
    main()
