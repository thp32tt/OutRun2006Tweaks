#!/usr/bin/env python3
"""Source graph + destructive regressions: original D3D9 BC material -> native GPU Draw."""
from pathlib import Path
src = Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
codec = Path("src/vr/d3d11/live_game_block_compressed_texture.hpp").read_text()
def integrated(source,h):
    return all(s in source for s in (
        '#include "live_game_block_compressed_texture.hpp"',
        'const auto blockLayout = block_texture::from_d3d9_format(',
        'const bool legacyBlock = blockLayout != block_texture::Layout::unsupported;',
        'if (legacyBlock && !block_texture::sampleable(blockLayout, capture.srgbTexture))',
        '|| legacyBlock;',
        'block_texture::bytes_per_block(blockLayout)',
        'DXGI_FORMAT_BC2_UNORM','DXGI_FORMAT_BC3_UNORM',
        'DXGI_FORMAT_BC4_UNORM','DXGI_FORMAT_BC5_UNORM',
        'block_texture::copy_row(source, destination, desc.Width, blockLayout)',
        'mirrorLiveSampler(capture, views[slot], samplers[slot])',
        'mirror_texture(device, captured, view, sampler)',
    )) and all(s in h for s in (
        'case 0x32545844u: return Layout::premul_bc2;',
        'case 0x34545844u: return Layout::premul_bc3;',
        'case 0x31495441u: return Layout::bc4;',
        'case 0x32495441u: return Layout::bc5;',
        'return !srgb && bytes_per_block(kind) != 0u;',
        'std::memcpy(destination, source, bytes);',
        '(static_cast<std::uint64_t>(width) + 3u) / 4u',
    ))
assert integrated(src,codec), "01069 native BC game source graph missing"
negatives=[
    (src.replace('DXGI_FORMAT_BC4_UNORM','DXGI_FORMAT_BC1_UNORM',1),codec),
    (src.replace('DXGI_FORMAT_BC5_UNORM','DXGI_FORMAT_BC3_UNORM',1),codec),
    (src.replace('block_texture::copy_row(source, destination, desc.Width, blockLayout)','std::memcpy(destination,source,rowBytes)',1),codec),
    (src.replace('if (legacyBlock && !block_texture::sampleable(blockLayout, capture.srgbTexture))','if (false)',1),codec),
    (src,codec.replace('case 0x32495441u: return Layout::bc5;','case 0x32495441u: return Layout::unsupported;',1)),
    (src,codec.replace('return !srgb && bytes_per_block(kind) != 0u;','return bytes_per_block(kind) != 0u;',1)),
    (src,codec.replace('std::memcpy(destination, source, bytes);','std::memset(destination,0,bytes);',1)),
    (src,codec.replace('(static_cast<std::uint64_t>(width) + 3u) / 4u','static_cast<std::uint64_t>(width) / 4u',1)),
]
assert all(not integrated(*x) for x in negatives), "01069 negative mutation not detected"
print("01069 PASS BC material GPU Draw graph & destructive negative regressions")
