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
    // TEX2: the live stage 0 can source either UV set from real vertex bytes.
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex2, layout));
    assert(layout.texcoordCount == 2u && layout.minStride == 32u);
    struct RhwUv2 {float x,y,z,rhw,u0,v0,u1,v1;};
    RhwUv2 twice{1,2,.4f,1,.1f,.2f,.7f,.8f};
    assert(game_fvf_decode_vertex(&twice, sizeof(twice), layout, sample));
    float chosen[2] = {-1.f, -1.f};
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .7f && chosen[1] == .8f);
    assert(game_fvf_select_uv(sample, layout, 0u, chosen));
    assert(chosen[0] == .1f && chosen[1] == .2f);
    const auto safe = sample;
    assert(!game_fvf_decode_vertex(&twice, 31u, layout, sample));
    assert(sample.uv1[0] == safe.uv1[0]);
    assert(!game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .1f && chosen[1] == .2f);
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex1 | kGameFvfTex2, layout));
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex2 | 0x00010000u, layout));
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfDiffuse | kGameFvfTex2, layout));
    assert(layout.texcoordOffset == 16u && layout.minStride == 32u);
    struct XyzColorUv2 {float x,y,z; std::uint32_t color; float u0,v0,u1,v1;};
    XyzColorUv2 color2{1,2,3,0xff010203u,.1f,.2f,.3f,.4f};
    assert(game_fvf_decode_vertex(&color2, sizeof(color2), layout, sample));
    assert(sample.diffuse == 0xff010203u && sample.uv1[0] == .3f);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfTex1, layout));
    assert(!game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .1f);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfDiffuse, layout));
    assert(!layout.textured && layout.minStride == 16);
    return 0;
}
