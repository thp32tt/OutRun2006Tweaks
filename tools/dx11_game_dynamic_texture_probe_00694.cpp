// D3D9 DEFAULT DYNAMIC texture source -> fresh per-Draw native mip snapshots.
#include "../src/vr/d3d11/live_game_dynamic_texture.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
namespace dt = outrun::vr::dx11::live_game_frame::dynamic_texture;

template<std::size_t Pitch, std::size_t Rows>
bool snapshot(const std::array<std::uint8_t, Pitch*Rows>& game,
              unsigned rowBytes, std::array<std::uint8_t, Rows*8>& out) {
    if (!dt::readable_pitch(Pitch, rowBytes) || rowBytes > 8) return false;
    for (std::size_t y=0; y<Rows; ++y)
        std::memcpy(out.data()+y*8, game.data()+y*Pitch, rowBytes);
    return true;
}
int main() {
    using R=dt::SourceRoute;
    static_assert(dt::source_route(0, 0x200, false) == R::dynamic_default);
    static_assert(dt::source_route(0, 0, false) == R::unsupported);
    static_assert(dt::source_route(0, 0x600, false) == R::unsupported);
    static_assert(dt::source_route(0, 0x201, false) == R::unsupported);
    static_assert(dt::source_route(0, 0x1, true) == R::render_target_readback);
    static_assert(dt::source_route(1, 0, false) == R::cpu_lockable);
    static_assert(dt::source_route(2, 0, false) == R::cpu_lockable);
    static_assert(dt::readable_pitch(12, 8));
    static_assert(!dt::readable_pitch(-8, 8));
    static_assert(!dt::readable_pitch(7, 8));
    static_assert(!dt::readable_pitch(8, 0));
    // Two game-authored 2x2 RGBA texels, with poisonous pitch padding.
    // A subsequent game update must upload NEW pixels, not a cached frame.
    constexpr std::array<std::uint8_t,24> menu{{
        1,2,3,4,5,6,7,8,0xee,0xee,0xee,0xee,
        9,10,11,12,13,14,15,16,0xdd,0xdd,0xdd,0xdd
    }};
    constexpr std::array<std::uint8_t,24> race{{
        51,52,53,54,55,56,57,58,0xaa,0xaa,0xaa,0xaa,
        59,60,61,62,63,64,65,66,0xbb,0xbb,0xbb,0xbb
    }};
    std::array<std::uint8_t,16> first{}, second{};
    if (!snapshot(menu,8,first) || !snapshot(race,8,second) ||
        first==second || first[0]!=1 || second[0]!=51 ||
        first[8]!=9 || second[8]!=59 || menu[8]!=0xee) return 1;
    // A separate 1x1 LOD uses its own LockRect/pitch each time.
    constexpr std::array<std::uint8_t,12> mip{{21,22,23,24,0xee,0xee,0xee,0xee,0xee,0xee,0xee,0xee}};
    std::array<std::uint8_t,8> lod{};
    if (!snapshot(mip,4,lod) || lod[0]!=21 || lod[3]!=24) return 2;
    if (dt::readable_pitch(3,4) || snapshot(mip,13,lod)) return 3;
    std::puts("00694 PASS: DEFAULT DYNAMIC source plan, two distinct Draw-frame snapshots, mips, pitch/fallback");
    return 0;
}
