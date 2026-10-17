#pragma once
#include <cstdint>
// D3DFMT_R8G8B8 has B,G,R bytes. Native BGRA8 adds opaque alpha.
namespace outrun::vr::dx11::live_game_frame::rgb24_texture {
constexpr unsigned source_bytes_per_texel() noexcept {return 3u;}
constexpr unsigned upload_bytes_per_texel() noexcept {return 4u;}
inline void unpack_row(const std::uint8_t* src, std::uint8_t* dst, unsigned width) noexcept {
  for (unsigned x=0; x<width; ++x) {
    dst[4u*x] = src[3u*x]; dst[4u*x+1] = src[3u*x+1];
    dst[4u*x+2] = src[3u*x+2]; dst[4u*x+3] = 255u;
  }
}
}
