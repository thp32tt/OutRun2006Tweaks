#include "../src/vr/d3d11/live_game_rgba_texture.hpp"
#include <array>
#include <algorithm>
#include <cassert>
#include <cstdint>
using outrun::vr::dx11::live_game_frame::rgba_texture::Layout;
using outrun::vr::dx11::live_game_frame::rgba_texture::unpack_row;
using outrun::vr::dx11::live_game_frame::rgba_texture::source_bytes_per_texel;
using outrun::vr::dx11::live_game_frame::rgba_texture::upload_bytes_per_texel;
int main() {
    static_assert(source_bytes_per_texel() == 4u && upload_bytes_per_texel() == 4u);
    // Two padded source rows mimic D3D9 LockRect Pitch > Width * 4.
    const std::array<std::uint8_t, 24> source{{12,34,56,78, 90,123,145,167, 99,99,99,99,
                                                11,22,33,44, 55,66,77,88, 99,99,99,99}};
    std::array<std::uint8_t, 20> target{};
    target.fill(201u);
    for (unsigned y = 0; y < 2u; ++y)
        unpack_row(source.data() + y * 12u, target.data() + y * 8u, 2u, Layout::argb);
    assert((target == std::array<std::uint8_t, 20>{{56,34,12,78, 145,123,90,167,
                                                    33,22,11,44, 77,66,55,88,
                                                    201,201,201,201}}));
    target.fill(201u);
    unpack_row(source.data(), target.data(), 2u, Layout::xrgb);
    assert((target == std::array<std::uint8_t, 20>{{56,34,12,255, 145,123,90,255,
                                                    201,201,201,201,201,201,201,201,201,201,201,201}}));
    // Subsequent 1x1 mip retains A8 alpha, but X8 must ignore garbage alpha.
    const std::array<std::uint8_t, 4> mip{{3, 67, 177, 19}};
    target.fill(201u);
    unpack_row(mip.data(), target.data(), 1u, Layout::argb);
    assert((std::array<std::uint8_t, 4>{{target[0],target[1],target[2],target[3]}} ==
            std::array<std::uint8_t, 4>{{177,67,3,19}}));
    unpack_row(mip.data(), target.data(), 1u, Layout::xrgb);
    assert((std::array<std::uint8_t, 4>{{target[0],target[1],target[2],target[3]}} ==
            std::array<std::uint8_t, 4>{{177,67,3,255}}));
    target.fill(201u);
    unpack_row(mip.data(), target.data(), 0u, Layout::xrgb);
    assert(std::all_of(target.begin(), target.end(), [](auto v){return v == 201u;}));
}
