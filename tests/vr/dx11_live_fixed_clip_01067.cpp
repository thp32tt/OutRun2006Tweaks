#include "../../src/vr/d3d11/live_game_fixed_clip.hpp"
#include <array>
#include <cassert>
#include <limits>
using namespace outrun::vr::dx11;
int main() {
    static_assert(native_game_fixed_clip_mask_admitted(0u,0u,true));
    static_assert(native_game_fixed_clip_mask_admitted(0x21u,6u,false));
    static_assert(!native_game_fixed_clip_mask_admitted(0x40u,8u,false));
    static_assert(!native_game_fixed_clip_mask_admitted(0x20u,5u,false));
    static_assert(!native_game_fixed_clip_mask_admitted(1u,6u,true));
    const float world[4][4]{{1.f,0.f,0.f,0.f},
        {0.f,1.f,0.f,0.f},{0.f,0.f,1.f,0.f},{4.f,0.f,0.f,1.f}};
    const float xyz[3]{-3.f,2.f,0.f};
    NativeGameFixedClipPlanes planes{};
    planes.mask=0x21u;
    planes.world[0]={1.f,0.f,0.f,0.f};
    planes.world[5]={0.f,-1.f,0.f,0.f};
    std::array<float,8> d{};
    assert(native_game_fixed_clip_distances(xyz,world,planes,d));
    assert(d[0]==1.f && d[5]==-2.f);
    assert(d[1]==1.f && d[4]==1.f && d[6]==1.f && d[7]==1.f);
    planes.mask=0u;
    assert(native_game_fixed_clip_distances(xyz,world,planes,d));
    for(float x:d) assert(x==1.f);
    planes.mask=1u;
    planes.world[0][0]=std::numeric_limits<float>::infinity();
    assert(!native_game_fixed_clip_distances(xyz,world,planes,d));
}
