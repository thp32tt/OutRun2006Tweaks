#!/usr/bin/env python3
"""Native D3D9 signed-normal material SRV: verify real game link and fail-closed cases.

Runs with the portable C++ row/format regression in the same DX11 Fast Gate.
"""
from pathlib import Path
src = Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = Path("src/vr/d3d11/live_game_signed_normal_texture.hpp").read_text()
def verified(code: str, h: str) -> bool:
    return all(x in code for x in (
        '#include "live_game_signed_normal_texture.hpp"',
        'const bool signedNormal = signed_normal_texture::sampleable(',
        'signedNormalLayout, capture.srgbTexture)',
        'signedNormalLayout != signed_normal_texture::Layout::unsupported',
        'DXGI_FORMAT_R8G8_SNORM',
        'DXGI_FORMAT_R8G8B8A8_SNORM',
        'DXGI_FORMAT_R16G16_SNORM',
        'nativeFormat == DXGI_FORMAT_R8G8_SNORM',
        'signedNormal ? signed_normal_texture::source_bytes_per_texel',
        'signed_normal_texture::copy_row(',
        'mirrorLiveSampler(capture, views[slot], samplers[slot])',
        'mirrorLiveSampler(capture,', 'mirror_texture(device, captured, view, sampler)',
    )) and all(x in h for x in (
        'case 60u: return Layout::uv8;',
        'case 63u: return Layout::uvwq8;',
        'case 64u: return Layout::uv16;',
        'case 62u: return Layout::unsupported;',
        'return !srgb && source_bytes_per_texel(l) != 0u;',
        'std::memcpy(native, source, bytes);',
        'width > (std::numeric_limits<std::uint32_t>::max)() / n',
    ))
assert verified(src, header), "Native VS/PS signed-normal texture Draw/Indexed source graph broken"
# Destructive tests are not promises about runtime pixels. They ensure the
# exact source path cannot pass after dropping an essential format, pitch,
# sampler, range or negative/sRGB rejection admission.
broken = [
    (src.replace('DXGI_FORMAT_R8G8_SNORM', 'DXGI_FORMAT_R8G8_UNORM'), header),
    (src.replace('DXGI_FORMAT_R16G16_SNORM', 'DXGI_FORMAT_R16G16_UNORM', 1), header),
    (src.replace('signedNormalLayout, capture.srgbTexture)', 'signedNormalLayout, false)', 1), header),
    (src.replace('signedNormal ? signed_normal_texture::source_bytes_per_texel', 'false ? signed_normal_texture::source_bytes_per_texel', 1), header),
    (src.replace('signed_normal_texture::copy_row(', 'std::memcpy(', 1), header),
    (src, header.replace('case 63u: return Layout::uvwq8;', 'case 63u: return Layout::unsupported;')),
    (src, header.replace('return !srgb && source_bytes_per_texel(l) != 0u;', 'return source_bytes_per_texel(l) != 0u;')),
    (src, header.replace('std::memcpy(native, source, bytes);', 'std::memset(native, 0, bytes);')),
]
assert all(not verified(*pair) for pair in broken), "Negative source-graph test must reject each mutation"
print("01068 PASS: signed normal map formats/pitch/Draw+Indexed sampler chain, sRGB/unsafe format negatives")