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
    std::cout << "game-authored GPU stretch source routes and cropped UV clamping PASS\n";
}
