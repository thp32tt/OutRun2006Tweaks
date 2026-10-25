#!/usr/bin/env python3
"""Source-connected game draw/Indexed and destructive regression."""
from pathlib import Path
src=Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
hdr=Path("src/vr/d3d11/live_game_mixed_bump_texture.hpp").read_text()
def integrated(s,h):
    return all(x in s for x in (
        '#include "live_game_mixed_bump_texture.hpp"',
        'mixed_bump_texture::from_d3d9_format(',
        'mixed_bump_texture::sampleable(',
        'nativeFormat = DXGI_FORMAT_R16G16B16A16_SNORM;',
        'nativeFormat == DXGI_FORMAT_R16G16B16A16_SNORM ||',
        'mixed_bump_texture::source_bytes_per_texel(mixedBumpLayout)',
        'const UINT uploadPitch = mixedBump ? desc.Width * 8u :',
        'mixed_bump_texture::unpack_row(',
        'mirrorLiveSampler(capture, views[slot], samplers[slot])',
        'mirror_texture(device, captured, view, sampler)',
    )) and all(x in h for x in (
        'f==61u ? Layout::l6v5u5',
        'f==62u ? Layout::x8l8v8u8',
        'f==117u ? Layout::cxv8u8',
        'return !srgb && source_bytes_per_texel(l)!=0u;',
        'if(remainder < -1e-10)return false;',
        'std::memcpy(dst+static_cast<std::size_t>(i)*8u,rgba.data(),8u);',
    ))
assert integrated(src,hdr),"01070 native Draw material source graph not connected"
negative=[
 (src.replace('nativeFormat = DXGI_FORMAT_R16G16B16A16_SNORM;','nativeFormat = DXGI_FORMAT_B8G8R8A8_UNORM;',1),hdr),
 (src.replace('const UINT uploadPitch = mixedBump ? desc.Width * 8u :','const UINT uploadPitch = mixedBump ? desc.Width * 4u :',1),hdr),
 (src.replace('mixed_bump_texture::unpack_row(','std::memcpy(',1),hdr),
 (src.replace('mixed_bump_texture::sampleable(','unsafe_sampleable(',1),hdr),
 (src,hdr.replace('f==117u ? Layout::cxv8u8','f==117u ? Layout::unsupported',1)),
 (src,hdr.replace('if(remainder < -1e-10)return false;','if(false)return false;',1)),
 (src,hdr.replace('return !srgb && source_bytes_per_texel(l)!=0u;','return source_bytes_per_texel(l)!=0u;',1)),
]
assert all(not integrated(a,b) for a,b in negative),"01070 destructive negative missed"
print("01070 PASS integrated native game bump samplers and negative mutations")
