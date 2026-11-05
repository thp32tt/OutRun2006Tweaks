// OutRun D3D9 A16B16G16R16 game LockRect -> native D3D11 R16G16B16A16 SRV.
#include "../src/vr/d3d11/live_game_rgba16_texture.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>

using outrun::vr::dx11::live_game_frame::rgba16_texture::copy_row;
using outrun::vr::dx11::live_game_frame::rgba16_texture::source_bytes_per_texel;
int main() {
    static_assert(source_bytes_per_texel() == 8u);
    // Two game texels per padded LockRect row: R,G,B,A are 16-bit LE values.
    constexpr std::array<std::uint8_t, 40> game{{
        0x34,0x12, 0x00,0x80, 0xff,0xff, 0x00,0x00,
        0xcd,0xab, 0x57,0x13, 0x68,0x24, 0xff,0xff,
        0xee,0xee,0xee,0xee,
        0x00,0x00, 0xff,0xff, 0x01,0x00, 0x00,0x80,
        0xff,0xff, 0x00,0x00, 0x00,0x00, 0xff,0x7f,
        0xdd,0xdd,0xdd,0xdd
    }};
    std::array<std::uint8_t, 32> upload{};
    copy_row(game.data(), upload.data(), 2);
    copy_row(game.data()+20, upload.data()+16, 2);
    if (std::memcmp(game.data(), upload.data(), 16) != 0 ||
        std::memcmp(game.data()+20, upload.data()+16, 16) != 0 ||
        upload[0] != 0x34 || upload[1] != 0x12 ||
        upload[5] != 0xff || upload[22] != 0x00 ||
        upload[31] != 0x7f) return 1;
    // 1x1 tail mip remains eight bytes: no 16->8 channel quantization.
    constexpr std::array<std::uint8_t, 8> mip{{0x01,0x23,0x45,0x67,0x89,0xab,0xcd,0xef}};
    std::array<std::uint8_t, 8> nativeMip{};
    copy_row(mip.data(), nativeMip.data(), 1);
    if (nativeMip != mip) return 2;
    std::puts("00669 PASS: padded game RGBA16 rows, 64-bit channels and 1x1 mip");
}
