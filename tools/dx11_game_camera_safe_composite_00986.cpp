#include "../src/vr/d3d11/native_game_offscreen_color_provenance.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11;
using Key=NativeGameOffscreenColorKey;
using Region=NativeGameOffscreenColorRegion;
int main() {
    constexpr Key cam{0xCAFEu,0u,0u}, eyeR{0xCAFEu,1u,0u}, mip1{0xCAFEu,0u,1u};
    constexpr std::array<Key,5> keys{{cam,cam,cam,eyeR,mip1}};
    constexpr std::array<Region,5> areas{{
        {0u,0u,2u,4u},{2u,0u,4u,2u},{2u,2u,4u,4u},
        {4u,0u,8u,4u},{0u,4u,4u,8u}}};
    // Genuine camera Draw/Clear tiles fill a COPY or visible STRETCH crop.
    static_assert(native_game_gpu_eye_composite_source_proven(
        cam,{0u,0u,4u,4u},keys,areas,5u));
    static_assert(native_game_gpu_eye_composite_source_proven(
        cam,{1u,1u,3u,3u},keys,areas,5u));
    // Never borrow pixels from an alien eye or a different mip.
    static_assert(!native_game_gpu_eye_composite_source_proven(
        cam,{0u,0u,5u,4u},keys,areas,5u));
    static_assert(!native_game_gpu_eye_composite_source_proven(
        cam,{0u,0u,4u,5u},keys,areas,5u));
    static_assert(!native_game_gpu_eye_composite_source_proven(
        eyeR,{0u,0u,4u,4u},keys,areas,5u));
    constexpr std::array<Key,2> partialKeys{{cam,cam}};
    constexpr std::array<Region,2> partial{{{0u,0u,2u,4u},{2u,0u,4u,3u}}};
    static_assert(!native_game_gpu_eye_composite_source_proven(
        cam,{0u,0u,4u,4u},partialKeys,partial,2u));
    assert(!native_game_gpu_eye_composite_source_proven(
        cam,{},keys,areas,5u));
    assert(!native_game_gpu_eye_composite_source_proven(
        {},{0u,0u,1u,1u},keys,areas,5u));
}
