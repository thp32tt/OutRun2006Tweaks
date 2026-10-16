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
    std::cout << "game-authored GPU stretch source routes PASS\n";
}
