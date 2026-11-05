#include "src/vr/d3d11/native_game_offscreen_color_provenance.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11;
int main() {
    NativeGameOffscreenColorProvenanceState camera;
    assert(camera.allows_postpass(false,false));
    assert(camera.allows_postpass(true,true));
    assert(!camera.allows_postpass(true,false));
    std::array<NativeGameOffscreenColorRegion,32> stripes{};
    for(std::uint32_t i=0;i<32;i++) stripes[i]={4u*i,0u,4u*i+4u,16u};
    assert(native_game_offscreen_color_region_fully_covered(
        {0u,0u,128u,16u},stripes,stripes.size()));
    assert(!native_game_offscreen_color_region_fully_covered(
        {0u,0u,132u,16u},stripes,stripes.size()));
    camera.note_untracked_gpu_write(); // 33rd game GPU camera Write
    assert(!camera.allows_postpass(false,false)); // not "untouched"
    assert(!camera.allows_postpass(true,true));   // no stale eye
    assert(!camera.allows_postpass(false,true));
    NativeGameOffscreenColorProvenanceState nextEye;
    assert(nextEye.allows_postpass(true,true)); // no cross-eye poisoning
    return 0;
}
