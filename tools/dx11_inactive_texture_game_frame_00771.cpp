// Real OutRun TEX1..8 menu/vehicle/race diffuse-only stage with a stale
// D3D9 texture: use the same native Draw/Indexed geometry, not a texture SRV.
#include "../src/vr/d3d11/live_game_fvf_layout.hpp"
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool bypass(unsigned op,unsigned a1,unsigned a2,unsigned ao,
                      unsigned aa1,unsigned aa2,unsigned next,bool diff=true) {
    return game_fvf_diffuse_only_inactive_texture(
        op,a1,a2,ao,aa1,aa2,next,diff);
}
static_assert(bypass(1, ~0u, ~0u, 1, ~0u, ~0u, 1)); // stage disabled
static_assert(bypass(2, 0, 2, 3, 2, 1, 1));       // RGB diffuse, alpha CURRENT
static_assert(bypass(3, 2, 1, 2, 0, 2, 1));       // RGB CURRENT, alpha diffuse
static_assert(!bypass(2, 2, 0, 2, 0, 2, 1));      // RGB samples TEXTURE
static_assert(!bypass(2, 0, 2, 2, 2, 0, 1));      // alpha samples TEXTURE
static_assert(!bypass(2, 0, 2, 2, 0, 2, 4));      // stage 1 active
static_assert(!bypass(1, 0, 0, 1, 0, 0, 4));      // invalid downstream stage
static_assert(!bypass(1, 0, 0, 1, 0, 0, 1,false));// no source DIFFUSE
int main() {
    GameFvfLayout menu{}, vehicle{}, noDiffuse{};
    if (!game_fvf_layout(kGameFvfXyzRhw | kGameFvfDiffuse | kGameFvfTex1,menu)
        || !menu.textured || !menu.hasDiffuse || menu.minStride != 28u)
        return 1;
    if (!game_fvf_layout(kGameFvfXyz | kGameFvfDiffuse | kGameFvfTex2,vehicle)
        || !vehicle.textured || !vehicle.hasDiffuse || vehicle.minStride != 32u)
        return 2;
    if (!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex1,noDiffuse)
        || noDiffuse.hasDiffuse || bypass(1,0,0,1,0,0,1,noDiffuse.hasDiffuse))
        return 3;
    return 0;
}
