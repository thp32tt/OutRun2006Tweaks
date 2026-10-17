// Real OutRun TEX1..8 menu/vehicle/race diffuse-only stage with a stale
// D3D9 texture: use the same native Draw/Indexed geometry, not a texture SRV.
#include "../src/vr/d3d11/live_game_fvf_layout.hpp"
#include <limits>
#include <cmath>
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

    // Draw->Indexed continuation: an inactive TEX1 stage must not read
    // nonfinite unused UVs as color or move the source DIFFUSE offset.
    // The native bridge zeros unsampled UV registers before GPU submission.
    std::uint8_t vertex[28]{};
    const float xyzw[4] = {12.f, 20.f, 0.5f, 1.f};
    const std::uint32_t color = 0xaabbccddU;
    const float staleUv[2] = {std::numeric_limits<float>::quiet_NaN(), 8.f};
    std::memcpy(vertex, xyzw, sizeof(xyzw));
    std::memcpy(vertex + menu.diffuseOffset, &color, sizeof(color));
    std::memcpy(vertex + menu.texcoordOffset, staleUv, sizeof(staleUv));
    GameFvfSample source{};
    if (!game_fvf_decode_vertex(vertex, sizeof(vertex), menu, source) ||
        source.diffuse != color || !std::isnan(source.uv[0]))
        return 4;
    if (!bypass(2, 0u, 2u, 2, 1u, 2u, 1u))
        return 5; // inactive TEXn still selects native diffuse-only PS
    return 0;
}
