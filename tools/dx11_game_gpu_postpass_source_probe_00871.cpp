#include "../../src/vr/d3d11/native_game_stretch_source.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    constexpr auto RT=0x20u, SRV=0x8u, UAV=0x80u;
    // Real separately posed menu/car/race GPU-only camera outputs survive
    // admission for each eye; format conversion goes through CopyToSampled.
    static_assert(native_game_postpass_gpu_source(0u,1u,RT,SRV,UAV));
    static_assert(native_game_postpass_gpu_source(UAV,1u,RT,SRV,UAV));
    static_assert(native_game_postpass_gpu_source(RT,4u,RT,SRV,UAV));
    static_assert(native_game_postpass_gpu_source(SRV,1u,RT,SRV,UAV));
    assert(native_game_stretch_source_transfer(
        1u,1u,0u,false,false,true,true,false,true) ==
        NativeGameStretchSourceTransfer::CopyToSampled);
    assert(native_game_copy_clipped_region(
        1920u,1080u,0u,0u,1920u,1080u,1920u,1080u,-32,-8).sourceLeft==32u);
    // Invalid copy-only MSAA, depth-only, zero-sample, unresolvable
    // source and off-eye crops must leave the original D3D9 frame intact.
    assert(!native_game_postpass_gpu_source(0u,4u,RT,SRV,UAV));
    assert(!native_game_postpass_gpu_source(UAV,4u,RT,SRV,UAV));
    assert(!native_game_postpass_gpu_source(0x2u,1u,RT,SRV,UAV));
    assert(!native_game_postpass_gpu_source(0u,0u,RT,SRV,UAV));
    assert(native_game_stretch_source_transfer(
        1u,4u,0u,false,false,true,true,true,true) ==
        NativeGameStretchSourceTransfer::Reject);
    assert(!native_game_copy_clipped_region(
        1920u,1080u,0u,0u,1920u,1080u,1920u,1080u,1920,0).valid);
}
