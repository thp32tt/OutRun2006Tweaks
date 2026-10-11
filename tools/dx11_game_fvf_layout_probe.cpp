#include "../src/vr/d3d11/live_game_fvf_layout.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    GameFvfLayout layout{};
    const auto original = layout;
    assert(!game_fvf_layout(kGameFvfXyz | kGameFvfTex1 | 0x200u, layout));
    assert(layout.minStride == original.minStride);
    assert(!game_fvf_layout(kGameFvfXyz, layout));
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfXyz | kGameFvfTex1, layout));
    assert(!game_fvf_layout(kGameFvfXyz | kGameFvfTex1 | 0x010u, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex1, layout));
    assert(layout.pretransformed && layout.textured && !layout.hasDiffuse);
    assert(layout.positionBytes == 16 && layout.texcoordOffset == 16 && layout.minStride == 24);
    struct RhwUv { float x, y, z, rhw, u, v; } rhwUv{11,22,0.5f,2,0.25f,0.75f};
    GameFvfSample sample{};
    assert(game_fvf_decode_vertex(&rhwUv, sizeof(rhwUv), layout, sample));
    assert(sample.position[3] == 2.f && sample.diffuse == 0xffffffffu);
    assert(sample.uv[0] == 0.25f && sample.uv[1] == 0.75f);
    const auto before = sample;
    assert(!game_fvf_decode_vertex(&rhwUv, 23, layout, sample));
    assert(sample.uv[1] == before.uv[1] && sample.diffuse == before.diffuse);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfTex1, layout));
    assert(!layout.pretransformed && !layout.hasDiffuse && layout.minStride == 20);
    struct XyzUv { float x,y,z,u,v; } xyzUv{1,2,3,.4f,.8f};
    assert(game_fvf_decode_vertex(&xyzUv, sizeof(xyzUv), layout, sample));
    assert(sample.position[3] == 1.f && sample.uv[0] == .4f);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfDiffuse | kGameFvfTex1, layout));
    assert(layout.texcoordOffset == 20 && layout.minStride == 28 && layout.hasDiffuse);
    struct ColoredRhwUv {float x,y,z,rhw; std::uint32_t color; float u,v;};
    ColoredRhwUv colored{1,2,3,1,0xaabbccdd,.2f,.6f};
    assert(game_fvf_decode_vertex(&colored, sizeof(colored), layout, sample));
    assert(sample.diffuse == 0xaabbccddu && sample.uv[0] == .2f);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfDiffuse, layout));
    assert(!layout.textured && layout.minStride == 16);
    return 0;
}
