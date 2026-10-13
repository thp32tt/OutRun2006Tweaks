#!/usr/bin/env python3
"""00670: live game half/full float RGBA mips -> native D3D11 Draw."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HDR = ROOT / "src/vr/d3d11/live_game_float_rgba_texture.hpp"
PROBE = ROOT / "tools/dx11_game_float_rgba_probe.cpp"

def linked(src, header, probe):
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = src.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    required = (
        "const bool floatRgba = base.Format == D3DFMT_A16B16G16R16F ||",
        "base.Format == D3DFMT_A32B32G32R32F;",
        "if (capture.srgbTexture && floatRgba) return false;",
        "DXGI_FORMAT_R16G16B16A16_FLOAT : DXGI_FORMAT_R32G32B32A32_FLOAT;",
        "floatRgba ? float_rgba_texture::source_bytes_per_texel(floatLayout) :",
        "else if (floatRgba)\n                    float_rgba_texture::copy_row(source, destination, desc.Width, floatLayout);",
        "static_cast<UINT>(lock.Pitch) >= rowBytes",
        "if (base.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;",
        "initial[level].SysMemPitch = pitches[level];",
        "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
        "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
    )
    return (
        '#include "live_game_float_rgba_texture.hpp"' in src
        and all(s in mirror for s in required)
        and all(s in draw for s in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        ))
        and all(s in header for s in (
            "enum class Layout : std::uint8_t { rgba16f, rgba32f };",
            "format == Layout::rgba16f ? 8u : 16u;",
            "std::memcpy(destination, source,",
            "static_cast<std::size_t>(width) * source_bytes_per_texel(format)",
        ))
        and all(s in probe for s in (
            "game16.data()+24", "game32.data()+24", "nativeMip != halfMip",
            "t::copy_row(", "std::memcmp(",
        ))
    )

def main():
    src, header, probe = SRC.read_text(), HDR.read_text(), PROBE.read_text()
    assert linked(src, header, probe), "float texture->SRV->Draw not connected"
    mutations = (
        ('#include "live_game_float_rgba_texture.hpp"', '#include "live_game_rgba16_texture.hpp"'),
        ("const bool floatRgba = base.Format == D3DFMT_A16B16G16R16F ||", "const bool floatRgba = false ||"),
        ("base.Format == D3DFMT_A32B32G32R32F;", "false;"),
        ("if (capture.srgbTexture && floatRgba) return false;", "if (false && floatRgba) return false;"),
        ("DXGI_FORMAT_R16G16B16A16_FLOAT : DXGI_FORMAT_R32G32B32A32_FLOAT;", "DXGI_FORMAT_B8G8R8A8_UNORM : DXGI_FORMAT_B8G8R8A8_UNORM;"),
        ("floatRgba ? float_rgba_texture::source_bytes_per_texel(floatLayout) :", "floatRgba ? 4u :"),
        ("float_rgba_texture::copy_row(source, destination, desc.Width, floatLayout);", "std::memcpy(destination, source, desc.Width * 4u);"),
        ("static_cast<UINT>(lock.Pitch) >= rowBytes", "false"),
        ("initial[level].SysMemPitch = pitches[level];", "initial[level].SysMemPitch = 0u;"),
        ("ctx->PSSetShaderResources(0, 1, &boundView);", "ctx->PSSetShaderResources(0, 0, &boundView);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    )
    for old, bad in mutations:
        assert old in src and not linked(src.replace(old, bad, 1), header, probe), old
    for old, bad in (
        ("format == Layout::rgba16f ? 8u : 16u;", "format == Layout::rgba16f ? 4u : 4u;"),
        ("std::memcpy(destination, source,", "std::memset(destination, 0,"),
    ):
        assert old in header and not linked(src, header.replace(old, bad, 1), probe), old
    for old, bad in (
        ("game32.data()+24", "game32.data()+16"),
        ("nativeMip != halfMip", "nativeMip == halfMip"),
    ):
        assert old in probe and not linked(src, header, probe.replace(old, bad)), old
    print("00670 PASS: 16 destructive float RGBA integration regressions; HMD/gamepad UNTESTED")

if __name__ == "__main__":
    main()
