#include "../src/vr/d3d11/native_game_stretch_source.hpp"
#include <cassert>
#include <iostream>

int main() {
    using outrun::vr::dx11::native_game_stretch_source_transfer;
    using outrun::vr::dx11::NativeGameStretchSourceTransfer;
    using E = NativeGameStretchSourceTransfer;
    // Menu atlas (several mips), shader-readable: sample mip zero directly.
    assert(native_game_stretch_source_transfer(5,1,0,true,true,true,true,false)
           == E::DirectSample);
    // Car/race postprocess: an RTV-only color source needs a GPU copy to
    // an SRV even when its original texture has several mip levels.
    assert(native_game_stretch_source_transfer(4,1,0,true,false,true,true,false)
           == E::CopyToSampled);
    // Real MSAA race RT: GPU resolve before the scaled shader postpass.
    assert(native_game_stretch_source_transfer(1,4,0,true,false,true,true,true)
           == E::ResolveToSampled);
    // A non-RT source cannot be resolved; one mip only for MSAA.
    assert(native_game_stretch_source_transfer(1,4,0,false,true,true,true,true)
           == E::Reject);
    assert(native_game_stretch_source_transfer(2,4,0,true,true,true,true,true)
           == E::Reject);
    assert(native_game_stretch_source_transfer(1,4,0,true,true,true,true,false)
           == E::Reject);
    // Unsupported typed sampling, eye writes and source access must fail
    // closed instead of accepting an invalid OpenXR eye draw.
    assert(native_game_stretch_source_transfer(1,1,0,true,true,false,true,true)
           == E::Reject);
    assert(native_game_stretch_source_transfer(1,1,0,true,true,true,false,true)
           == E::Reject);
    assert(native_game_stretch_source_transfer(1,1,0,false,false,true,true,true)
           == E::Reject);
    assert(native_game_stretch_source_transfer(1,1,1,true,true,true,true,true)
           == E::Reject);
    // Cropped game atlas source -> scaled native eye: HLSL must clamp
    // bilinear UVs to the centres of the first and last admitted texels.
    using outrun::vr::dx11::native_game_stretch_uv_region;
    constexpr auto atlas = native_game_stretch_uv_region(8u,4u,2u,1u,5u,3u);
    static_assert(atlas.valid);
    static_assert(atlas.constants[0] == .25f &&
                  atlas.constants[1] == .25f);
    static_assert(atlas.constants[2] == .375f &&
                  atlas.constants[3] == .5f);
    static_assert(atlas.constants[4] == .3125f &&
                  atlas.constants[5] == .375f);
    static_assert(atlas.constants[6] == .5625f &&
                  atlas.constants[7] == .625f);
    // A one-texel crop may not sample the adjacent texture-array/atlas tile.
    constexpr auto single = native_game_stretch_uv_region(4u,4u,2u,3u,3u,4u);
    static_assert(single.valid && single.constants[4] == single.constants[6]);
    static_assert(single.constants[5] == single.constants[7]);
    // Fail closed on an invalid source box; no invalid divisions into a CB.
    static_assert(!native_game_stretch_uv_region(0u,4u,0u,0u,1u,1u).valid);
    static_assert(!native_game_stretch_uv_region(4u,4u,2u,2u,2u,3u).valid);
    static_assert(!native_game_stretch_uv_region(4u,4u,2u,2u,5u,3u).valid);
    // Real native GPU StretchRect clips destination geometry while keeping
    // the original game-authored texture-to-screen mapping (no edge zoom).
    using outrun::vr::dx11::native_game_stretch_clipped_region;
    constexpr auto cropped = native_game_stretch_clipped_region(
        8, 4, 2, 1, 6, 3, 4, 4, -2, 1, 6, 5);
    static_assert(cropped.valid && cropped.left == 0 &&
                  cropped.top == 1 && cropped.right == 4 &&
                  cropped.bottom == 4);
    static_assert(cropped.uv.constants[0] == .375f &&
                  cropped.uv.constants[1] == .25f &&
                  cropped.uv.constants[2] == .25f &&
                  cropped.uv.constants[3] == .375f);
    static_assert(cropped.uv.constants[4] == .3125f &&
                  cropped.uv.constants[6] == .6875f);
    // Top/right crop moves V start and shortens U, without altering
    // the source atlas clamp shared by linear and point filtering.
    constexpr auto otherEdge = native_game_stretch_clipped_region(
        8, 4, 2, 0, 6, 4, 4, 4, 1, -2, 5, 2);
    static_assert(otherEdge.valid && otherEdge.left == 1 &&
                  otherEdge.top == 0 && otherEdge.right == 4 &&
                  otherEdge.bottom == 2);
    static_assert(otherEdge.uv.constants[0] == .25f &&
                  otherEdge.uv.constants[1] == .5f &&
                  otherEdge.uv.constants[2] == .375f &&
                  otherEdge.uv.constants[3] == .5f);
    // Fully contained rectangles still use identical original UVs.
    constexpr auto whole = native_game_stretch_clipped_region(
        8, 4, 2, 1, 5, 3, 10, 10, 1, 2, 5, 6);
    static_assert(whole.valid && whole.uv.constants[0] == atlas.constants[0] &&
                  whole.uv.constants[1] == atlas.constants[1] &&
                  whole.uv.constants[2] == atlas.constants[2] &&
                  whole.uv.constants[3] == atlas.constants[3]);
    // No uncovered eye writes or invalid destination/source extents.
    static_assert(!native_game_stretch_clipped_region(
        8, 4, 2, 1, 6, 3, 4, 4, -9, 1, -5, 3).valid);
    static_assert(!native_game_stretch_clipped_region(
        8, 4, 2, 1, 6, 3, 4, 4, 1, 5, 3, 7).valid);
    static_assert(!native_game_stretch_clipped_region(
        8, 4, 2, 1, 6, 3, 4, 4, 2, 1, 2, 3).valid);
    static_assert(!native_game_stretch_clipped_region(
        8, 4, 7, 1, 9, 3, 4, 4, 1, 1, 3, 3).valid);
    static_assert(!native_game_stretch_clipped_region(
        8, 4, 2, 1, 6, 3, 0, 4, 1, 1, 3, 3).valid);
    std::cout << "game-authored GPU stretch source routes, clipped destination and cropped UV PASS\n";
}
