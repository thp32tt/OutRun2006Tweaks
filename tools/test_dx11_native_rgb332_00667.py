#!/usr/bin/env python3
"""00667 game D3D9 RGB332/ARGB8332 mip -> BGRA8 -> live native D3D11 Draw."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HDR = ROOT / "src/vr/d3d11/live_game_rgb332_texture.hpp"
PROBE = ROOT / "tools/dx11_game_rgb332_probe.cpp"
def linked(s,h):
    try:
        mirror = s.split("bool mirror_texture(",1)[1].split("bool submit(",1)[0]
        draw = s.split("bool submit(",1)[1].split("void before_game_present(",1)[0]
    except IndexError:
        return False
    return '#include "live_game_rgb332_texture.hpp"' in s and all(x in mirror for x in (
        "base.Format == D3DFMT_R3G3B2 ||",
        "base.Format == D3DFMT_A8R3G3B2;",
        "if (capture.srgbTexture && rgb332) return false;",
        "if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
        "else if (rgb332) {",
        "nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;",
        "rgb332 ? rgb332_texture::source_bytes_per_texel(rgb332Layout) :",
        "|| extendedLuma || rgb332 || p8 ?",
        "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
        "pitches[level] = a8p8UploadPitch;",
        "else if (rgb332)\n                    rgb332_texture::unpack_row(source, destination, desc.Width, rgb332Layout);",
        "initial[level].SysMemPitch = pitches[level];",
        "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
        "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
    )) and all(x in draw for x in (
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->PSSetShaderResources(0, 1, &boundView);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )) and all(x in h for x in (
        "Layout::a8rgb332 ? 2u : 1u",
        "const std::uint8_t color = source[in];",
        "bgra[out] = expand2(",
        "bgra[out + 1u] = expand3(",
        "bgra[out + 2u] = expand3(",
        "layout == Layout::a8rgb332 ? source[in + 1u] : 0xffu",
    ))
def main():
    s,h,p=SRC.read_text(),HDR.read_text(),PROBE.read_text()
    assert linked(s,h), "RGB332 live game Draw integration disconnected"
    assert all(x in p for x in ("row*4u","row*6u","row*8u","mip.data()",
                                "std::array<std::uint8_t,4>{85,36,182,29}"))
    mutations=(
        ('#include "live_game_rgb332_texture.hpp"','#include "live_game_rg16_texture.hpp"'),
        ("base.Format == D3DFMT_A8R3G3B2;", "base.Format == D3DFMT_X8R8G8B8;"),
        ("if (capture.srgbTexture && rgb332) return false;", "if (false && rgb332) return false;"),
        ("else if (rgb332) {","else if (rg16) {"),
        ("rgb332 ? rgb332_texture::source_bytes_per_texel(rgb332Layout) :","rgb332 ? 4u :"),
        ("|| extendedLuma || rgb332 || p8 ?","|| extendedLuma || p8 ?"),
        ("else if (rgb332)\n                    rgb332_texture::unpack_row(source, destination, desc.Width, rgb332Layout);",
         "else if (rgb332)\n                    std::memcpy(destination, source, rowBytes);"),
        ("initial[level].SysMemPitch = pitches[level];","initial[level].SysMemPitch = 0u;"),
        ("ctx->PSSetShaderResources(0, 1, &boundView);","ctx->PSSetShaderResources(0, 0, &boundView);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);","ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);","ctx->Draw(0, 0);"),
    )
    header_mutations=(
        ("Layout::a8rgb332 ? 2u : 1u","Layout::a8rgb332 ? 1u : 1u"),
        ("bgra[out] = expand2(","bgra[out] = expand3("),
        ("bgra[out + 1u] = expand3(","bgra[out + 1u] = expand2("),
        ("bgra[out + 2u] = expand3(","bgra[out + 2u] = expand2("),
        ("layout == Layout::a8rgb332 ? source[in + 1u] : 0xffu","0xffu"),
    )
    for old,bad in mutations:
        assert old in s and not linked(s.replace(old,bad,1),h),old
    for old,bad in header_mutations:
        assert old in h and not linked(s,h.replace(old,bad,1)),old
    print(f"00667 PASS: {len(mutations)+len(header_mutations)} destructive integration checks; HMD UNTESTED")
if __name__=="__main__":
    main()
