// 01063 native GPU game cameras: two physical eyes, typed-RTV-backed
// typeless BGRA transfer, no synthetic mono->stereo or gamma reinterpretation.
#include "../../src/vr/d3d11/native_game_eye_pair_sources.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    constexpr std::uint32_t unorm=87u, srgb=91u, typeless=90u;
    constexpr auto compatible=native_game_eye_format_transfer_admitted;
    assert(compatible(unorm, 0u, unorm, 1u, unorm, srgb, typeless));
    assert(compatible(srgb, 0u, srgb, 1u, unorm, srgb, typeless));
    assert(compatible(typeless, unorm, unorm, 1u, unorm, srgb, typeless));
    assert(compatible(typeless, srgb, srgb, 1u, unorm, srgb, typeless));
    assert(!compatible(typeless, srgb, unorm, 1u, unorm, srgb, typeless));
    assert(!compatible(typeless, unorm, srgb, 1u, unorm, srgb, typeless));
    assert(!compatible(srgb, srgb, unorm, 1u, unorm, srgb, typeless));
    assert(!compatible(typeless, unorm, unorm, 4u, unorm, srgb, typeless));
    assert(!compatible(typeless, 0u, unorm, 1u, unorm, srgb, typeless));
    assert(!compatible(28u, unorm, unorm, 1u, unorm, srgb, typeless));
    constexpr auto slices=native_game_eye_rtv_subresource_matches;
    assert(slices(2,3,2,2,2));
    assert(slices(0,0,0,0,1));
    assert(!slices(2,3,1,2,2));
    assert(!slices(2,3,2,0,3));
    assert(!slices(2,3,2,2,0));
    const std::array<std::uintptr_t,4> owned{{99,100,101,102}};
    assert(native_game_eye_pair_sources_admitted(7,8,owned));
    assert(!native_game_eye_pair_sources_admitted(7,7,owned));
    assert(!native_game_eye_pair_sources_admitted(7,100,owned));
    assert(native_game_eye_transfer(1,0,1,0,false)==NativeGameEyeTransfer::Copy);
    assert(native_game_eye_transfer(4,0,4,0,true)==NativeGameEyeTransfer::Resolve);
    assert(native_game_eye_transfer(4,0,1,0,true)==NativeGameEyeTransfer::Reject);
}