#!/usr/bin/env python3
"""00662: destructive contracts for game-authored 10-bit mips -> DX11 Draw."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HEADER = ROOT / "src/vr/d3d11/live_game_10bit_texture.hpp"
PROBE = ROOT / "tools/dx11_game_10bit_probe.cpp"

def connected(src, hdr):
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = src.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
        tenbit_branch = mirror.split("else if (tenBit)", 1)[1].split("else\n", 1)[0]
    except IndexError:
        return False
    return ('#include "live_game_10bit_texture.hpp"' in src and
        "base.Format == D3DFMT_A2B10G10R10 ?" in tenbit_branch and
        all(s in mirror for s in (
          "const bool tenBit = base.Format == D3DFMT_A2R10G10B10 ||",
          "base.Format == D3DFMT_A2B10G10R10;",
          "if (capture.srgbTexture && tenBit) return false;",
          "|| packed16 || luminance || rgb24 || rgbaSwizzle || tenBit",
          "static_cast<UINT>(lock.Pitch) >= rowBytes",
          "else if (tenBit)",
          "tenbit_texture::unpack_row(source, destination, desc.Width,",
          "base.Format == D3DFMT_A2B10G10R10 ?",
          "tenbit_texture::Layout::a2b10g10r10 :",
          "tenbit_texture::Layout::a2r10g10b10);",
          "initial[level].SysMemPitch = pitches[level];",
          "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
          "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
          "if (base.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;"))
        and all(s in draw for s in (
          "mirror_texture(dev, capture, sampledView, sampledSampler)",
          "ctx->PSSetShaderResources(0, 1, &boundView);",
          "ctx->DrawIndexed(indexCount, 0, 0);",
          "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
        and all(s in hdr for s in (
          "constexpr std::uint8_t expand10(unsigned channel)",
          "(channel * 255u + 511u) / 1023u",
          "((packed >> 30u) & 3u) * 85u",
          "Layout::a2r10g10b10 ?",
          "Bgra8{expand10(low), expand10(green), expand10(high), alpha}",
          "Bgra8{expand10(high), expand10(green), expand10(low), alpha}",
          "static_cast<std::uint32_t>(source[off + 3u]) << 24u")))

def main():
    src, hdr = SOURCE.read_text(), HEADER.read_text()
    assert connected(src, hdr), "D3D9 10bit mip -> SRV -> Draw chain disconnected"
    probe = PROBE.read_text()
    assert all(s in probe for s in (
      "static_assert", "Layout::a2r10g10b10", "Layout::a2b10g10r10",
      "0x000ffc00u", "0x40000000u", "expand10(512u)",
      "y * 12u", "0xaa,0xbb,0xcc,0xdd", "1u", "0u")), "CPU probe incomplete"
    mutants = (
      ('#include "live_game_10bit_texture.hpp"', '#include "live_game_rgb24_texture.hpp"'),
      ('const bool tenBit = base.Format == D3DFMT_A2R10G10B10 ||', 'const bool tenBit = false ||'),
      ('base.Format == D3DFMT_A2B10G10R10;', 'base.Format == D3DFMT_A8B8G8R8;'),
      ('if (capture.srgbTexture && tenBit) return false;', 'if (false && tenBit) return false;'),
      ('|| packed16 || luminance || rgb24 || rgbaSwizzle || tenBit',
       '|| packed16 || luminance || rgb24 || rgbaSwizzle'),
      ('static_cast<UINT>(lock.Pitch) >= rowBytes', 'false'),
      ('else if (tenBit)', 'else if (false)'),
      ('tenbit_texture::unpack_row(source, destination, desc.Width,',
       'std::memcpy(destination, source, rowBytes); //'),
      ('base.Format == D3DFMT_A2B10G10R10 ?', 'false ?'),
      ('tenbit_texture::Layout::a2b10g10r10 :', 'tenbit_texture::Layout::a2r10g10b10 :'),
      ('tenbit_texture::Layout::a2r10g10b10);', 'tenbit_texture::Layout::a2b10g10r10);'),
      ('initial[level].SysMemPitch = pitches[level];', 'initial[level].SysMemPitch = 0;'),
      ('dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())', 'false'),
      ('if (base.Pool == D3DPOOL_DEFAULT && !gpuRenderTarget) return false;', 'if (false) return false;'),
      ('mirror_texture(dev, capture, sampledView, sampledSampler)', 'false'),
      ('ctx->PSSetShaderResources(0, 1, &boundView);', 'ctx->PSSetShaderResources(0, 0, &boundView);'),
      ('ctx->DrawIndexed(indexCount, 0, 0);', 'ctx->DrawIndexed(0, 0, 0);'),
    )
    hdr_mutants = (
      ('(channel * 255u + 511u) / 1023u', '(channel * 255u) / 1023u'),
      ('((packed >> 30u) & 3u) * 85u', '((packed >> 30u) & 3u) * 80u'),
      ('Layout::a2r10g10b10 ?', 'Layout::a2b10g10r10 ?'),
      ('Bgra8{expand10(low), expand10(green), expand10(high), alpha}',
       'Bgra8{expand10(high), expand10(green), expand10(low), alpha}'),
      ('static_cast<std::uint32_t>(source[off + 3u]) << 24u',
       'static_cast<std::uint32_t>(source[off + 3u]) << 16u'),
    )
    for old, replacement in mutants:
        assert old in src, "missing source " + old
        # 00691 introduced an earlier DEFAULT RT admission ternary for
        # this format. Mutate the last (actual texel decoder) occurrence.
        if old == "base.Format == D3DFMT_A2B10G10R10 ?":
            prefix, match, suffix = src.rpartition(old)
            mutant = prefix + replacement + suffix if match else src
        else:
            mutant = src.replace(old, replacement, 1)
        assert not connected(mutant, hdr), "escaped " + old
    for old, replacement in hdr_mutants:
        assert old in hdr, "missing header " + old
        assert not connected(src, hdr.replace(old, replacement, 1)), "escaped " + old
    print(f"00662 PASS: {len(mutants) + len(hdr_mutants)} destructive integration checks; HMD UNTESTED")

if __name__ == "__main__":
    main()
