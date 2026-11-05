#include "../src/vr/d3d11/live_game_p8_texture.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame::p8_texture;
static_assert(source_bytes_per_texel() == 1u);
int main() {
    std::array<Rgba, 256> palette{};
    palette[2] = {200, 31, 4, 13};
    palette[7] = {6, 140, 250, 0};
    palette[255] = {255, 0, 99, 51};
    // Two game-authored rows, 3 P8 texels each, with 3 source padding bytes.
    constexpr std::array<std::uint8_t, 12> source{
        2, 7, 255, 0xee, 0xee, 0xee,
        255, 2, 7, 0xdd, 0xdd, 0xdd
    };
    std::array<std::uint8_t, 28> out{};
    out.fill(19u);
    for (unsigned row = 0; row < 2u; ++row)
        unpack_row(source.data() + row * 6u, out.data() + row * 14u,
                   3u, palette.data());
    assert((out == std::array<std::uint8_t, 28>{
        4, 31, 200, 13, 250, 140, 6, 0, 99, 0, 255, 51, 19, 19,
        99, 0, 255, 51, 4, 31, 200, 13, 250, 140, 6, 0, 19, 19
    }));
    // Last 1x1 mip still samples the currently selected palette entry.
    constexpr std::array<std::uint8_t, 3> mip{255, 0xab, 0xcd};
    out.fill(19u);
    unpack_row(mip.data(), out.data(), 1u, palette.data());
    assert((std::array<std::uint8_t, 4>{out[0], out[1], out[2], out[3]} ==
            std::array<std::uint8_t, 4>{99, 0, 255, 51}));
    // Devices without ALPHAPALETTE must use fully opaque P8 texels.
    for (auto& entry : palette) entry.alpha = 255u;
    unpack_row(mip.data(), out.data(), 1u, palette.data());
    assert(out[0] == 99u && out[3] == 255u);
    for (unsigned i = 4; i < out.size(); ++i) assert(out[i] == 19u);
}
