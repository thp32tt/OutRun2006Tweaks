#include "vr/d3d11/live_game_fvf_point_cull.hpp"
#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
struct Vertex { float clip[4]; float clipDistances[6]; };
static constexpr auto kClip = offsetof(Vertex, clipDistances);
static constexpr std::uint32_t kCapacity = 1024u;
static bool build(const Vertex* data, std::uint32_t vertices,
                  const std::uint32_t* indices, std::uint32_t elements,
                  std::uint32_t topology, std::uint32_t cull,
                  std::uint32_t mask, std::vector<std::uint32_t>& out,
                  std::uint32_t limit = kCapacity) {
    return game_fvf_culled_point_indices(
        data, sizeof(Vertex), vertices, indices, elements, topology, cull,
        kClip, mask, limit, out);
}
int main() {
    // Two real FVF game triangle index orderings with opposite screen faces:
    // screen-CW is negative NDC area, so CULL_CW keeps only the first.
    Vertex tri[]{
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.5f, .5f,.5f,1.f},{1,1,1,1,1,1}}
    };
    const std::uint32_t both[]{0,1,2, 2,1,0};
    std::vector<std::uint32_t> out;
    assert(build(tri, 3u, both, 6u, 4u, 2u, 0u, out));
    assert((out == std::vector<std::uint32_t>{0,1,2}));
    assert(build(tri, 3u, both, 6u, 4u, 3u, 0u, out));
    assert((out == std::vector<std::uint32_t>{2,1,0}));
    // Four-vertex indexed/unindexed strip retains original *global* strip
    // winding and duplicated occurrences when lowered to GPU POINTLIST.
    Vertex strip[]{
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.5f, .5f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f, .5f,.5f,1.f},{1,1,1,1,1,1}}
    };
    assert(build(strip,4u,nullptr,4u,5u,2u,0u,out));
    assert((out == std::vector<std::uint32_t>{0,1,2, 2,1,3}));
    const std::uint32_t permute[]{3u,2u,1u,0u};
    assert(build(strip,4u,permute,4u,5u,2u,0u,out));
    assert((out == std::vector<std::uint32_t>{3,2,1, 1,2,0}));
    const auto intact=out;
    // Never bypass source clip/IA and never mutate a previously validated
    // GPU index plan when a later original game triangle is malformed.
    const std::uint32_t bad[]{0u,1u,2u, 2u,1u,99u};
    assert(!build(strip,4u,bad,6u,4u,2u,0u,out));
    assert(out==intact);
    assert(!build(strip,4u,nullptr,4u,5u,2u,0u,out,3u));
    assert(out==intact);
    strip[2].clip[3]=0.f;
    assert(!build(strip,4u,nullptr,4u,5u,2u,0u,out));
    strip[2].clip[3]=1.f;
    strip[2].clip[2]=2.f;
    assert(!build(strip,4u,nullptr,4u,5u,2u,0u,out));
    strip[2].clip[2]=.5f;
    strip[2].clip[0]=2.f;
    assert(!build(strip,4u,nullptr,4u,5u,2u,0u,out));
    strip[2].clip[0]=-.5f;
    strip[0].clipDistances[0]=-1.f;
    assert(!build(strip,4u,nullptr,4u,5u,2u,1u,out));
    strip[0].clipDistances[0]=1.f;
    strip[0].clipDistances[0]=std::numeric_limits<float>::quiet_NaN();
    assert(!build(strip,4u,nullptr,4u,5u,2u,1u,out));
    strip[0].clipDistances[0]=1.f;
    assert(!build(strip,4u,nullptr,4u,5u,2u,0x40u,out));
    assert(out==intact);
    tri[1].clip[0]=tri[0].clip[0];
    tri[1].clip[1]=tri[0].clip[1];
    assert(!build(tri,3u,both,6u,4u,2u,0u,out));
    assert(out==intact);
}
