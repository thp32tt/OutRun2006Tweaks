#include "vr/d3d11/live_game_fvf_point_cull.hpp"
#include "vr/d3d11/live_game_fvf_point_clip.hpp"
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
    // CULL_NONE also consumes source triangles, not raw unique vertices:
    // native POINTLIST must preserve overlapping strip corners exactly.
    assert(build(strip,4u,nullptr,4u,5u,1u,0u,out));
    assert((out == std::vector<std::uint32_t>{0,1,2, 2,1,3}));
    assert(build(tri,3u,both,6u,4u,1u,0u,out));
    assert((out == std::vector<std::uint32_t>{0,1,2, 2,1,0}));
    // An original source triangle wholly beyond the homogeneous right
    // plane has no point pixels. Its following visible triangle is emitted
    // in the same indexed GPU Draw with its original source IA identifiers.
    Vertex mixed[]{
        {{2.f,-.5f,.5f,1.f},{-1,1,1,1,1,1}},
        {{3.f,-.5f,.5f,1.f},{-1,1,1,1,1,1}},
        {{2.f, .5f,.5f,1.f},{-1,1,1,1,1,1}},
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.5f, .5f,.5f,1.f},{1,1,1,1,1,1}}
    };
    assert(build(mixed,6u,nullptr,6u,4u,1u,0u,out));
    assert((out == std::vector<std::uint32_t>{3,4,5}));
    assert(build(mixed,6u,nullptr,6u,4u,2u,0u,out));
    assert((out == std::vector<std::uint32_t>{3,4,5}));
    // Outside on an active D3D9 user plane is equally invisible; do not
    // mistake a wholly clipped face for an unsupported crossing.
    mixed[0].clip[0]=-.5f;
    mixed[1].clip[0]= .5f;
    mixed[2].clip[0]=-.5f;
    assert(build(mixed,6u,nullptr,6u,4u,1u,1u,out));
    assert((out == std::vector<std::uint32_t>{3,4,5}));
    const auto safeVisible = out;
    mixed[0].clipDistances[0]=1.f; // partly user-clipped: new corners unknown
    assert(!build(mixed,6u,nullptr,6u,4u,1u,1u,out));
    assert(out==safeVisible);
    mixed[0].clipDistances[0]=-1.f;
    mixed[0].clip[0]=2.f; // partly homogeneous-clipped
    assert(!build(mixed,6u,nullptr,6u,4u,1u,0u,out));
    assert(out==safeVisible);
    mixed[0].clip[0]=-.5f;
    const std::uint32_t malformed[]{0,1,2,3,4,99};
    assert(!build(mixed,6u,malformed,6u,4u,1u,0u,out));
    assert(out==safeVisible);
    // Even all-trivially-invisible Draws do not issue empty GPU commands.
    assert(!build(mixed,3u,nullptr,3u,4u,1u,1u,out));
    assert(out==safeVisible);
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
    // Intersecting source triangles must generate homogeneous-clipped
    // GPU POINT vertices and preserve payload interpolation on two stages.
    struct ClipVertex { float clip[4],clip0[4],clip1[4],uv[2]; };
    const auto lerp=[](const ClipVertex& a,const ClipVertex& b,double t) {
        ClipVertex v{};
        for(unsigned i=0;i<4;++i) {
            v.clip[i]=static_cast<float>((1-t)*a.clip[i]+t*b.clip[i]);
            v.clip0[i]=static_cast<float>((1-t)*a.clip0[i]+t*b.clip0[i]);
            v.clip1[i]=static_cast<float>((1-t)*a.clip1[i]+t*b.clip1[i]);
        }
        for(unsigned i=0;i<2;++i)
            v.uv[i]=static_cast<float>((1-t)*a.uv[i]+t*b.uv[i]);
        return v;
    };
    std::vector<ClipVertex> source{
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1},{1,1,0,0},{0,0}},
        {{ 2.f,-.5f,.5f,1.f},{1,1,1,1},{1,1,0,0},{1,0}},
        {{-.5f, .5f,.5f,1.f},{1,1,1,1},{1,1,0,0},{0,1}}
    };
    std::vector<ClipVertex> clipped;
    assert(game_fvf_clipped_point_vertices(
        source,nullptr,3u,4u,1u,0u,64u,lerp,clipped));
    assert(clipped.size()==4u);
    for(const auto& v:clipped) {
        assert(v.clip[0]<=v.clip[3]+1.e-5f);
        assert(v.clip[0]>=-v.clip[3]-1.e-5f);
        assert(v.uv[0]>=0.f && v.uv[0]<=1.f);
    }
    source[1].clip0[0]=-1.f;
    assert(game_fvf_clipped_point_vertices(
        source,nullptr,3u,4u,1u,1u,64u,lerp,clipped));
    for(const auto& v:clipped) assert(v.clip0[0]>=-1.e-5f);
    const auto original=clipped;
    const std::uint32_t lateBad[]{0,1,99};
    assert(!game_fvf_clipped_point_vertices(
        source,lateBad,3u,4u,1u,1u,64u,lerp,clipped));
    assert(clipped.size()==original.size());
    assert(!game_fvf_clipped_point_vertices(
        source,nullptr,3u,4u,1u,1u,3u,lerp,clipped));
    assert(clipped.size()==original.size());
    source[0].clip[3]=0.f;
    assert(!game_fvf_clipped_point_vertices(
        source,nullptr,3u,4u,1u,0u,64u,lerp,clipped));
    source[0].clip[3]=1.f;
    // Back-facing partially clipped source triangles are eliminated by the
    // real D3D9 cull stage; following fully-visible faces still get points.
    Vertex backface[]{
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{ 2.f, .5f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.5f, .5f,.5f,1.f},{1,1,1,1,1,1}}
    };
    const std::uint32_t order[]{2,1,0,3,4,5};
    assert(build(backface,6u,order,6u,4u,2u,0u,out));
    assert((out==std::vector<std::uint32_t>{3,4,5}));

    // A real world-space WVP game triangle can straddle the eye plane.
    // GPU D3D11 triangle clipping would retain its visible polygon, while
    // the old CPU point-fill path discarded the entire original game Draw
    // merely because the third source corner had W<0. Clip before dividing
    // by W, then carry both UV stages and real shader attributes to POINTLIST.
    std::vector<ClipVertex> eyeCrossing{
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1},{1,1,0,0},{0,0}},
        {{ .5f,-.5f,.5f,1.f},{1,1,1,1},{1,1,0,0},{1,0}},
        {{ 0.f, .5f,.2f,-.2f},{1,1,1,1},{1,1,0,0},{.5f,1}}
    };
    std::vector<ClipVertex> eyePoints;
    assert(game_fvf_clipped_point_vertices(
        eyeCrossing,nullptr,3u,4u,1u,0u,64u,lerp,eyePoints));
    assert(eyePoints.size()>=3u);
    for (const auto& v:eyePoints) {
        assert(v.clip[3]>0.0f);
        assert(v.clip[0]>=-v.clip[3]-1.e-4f &&
               v.clip[0]<= v.clip[3]+1.e-4f);
        assert(v.clip[1]>=-v.clip[3]-1.e-4f &&
               v.clip[1]<= v.clip[3]+1.e-4f);
        assert(v.clip[2]>=-1.e-4f && v.clip[2]<=v.clip[3]+1.e-4f);
        assert(v.uv[0]>=0.f && v.uv[0]<=1.f);
        assert(v.uv[1]>=0.f && v.uv[1]<=1.f);
    }
    const auto validEyePoints=eyePoints;
    // Full transactional fallback when a late source IA value is invalid.
    const std::uint32_t malformedEye[]{0u,1u,99u};
    assert(!game_fvf_clipped_point_vertices(
        eyeCrossing,malformedEye,3u,4u,1u,0u,64u,lerp,eyePoints));
    assert(eyePoints.size()==validEyePoints.size());
    assert(!game_fvf_clipped_point_vertices(
        eyeCrossing,nullptr,3u,4u,1u,0u,2u,lerp,eyePoints));
    assert(eyePoints.size()==validEyePoints.size());
    eyeCrossing[2].clip[3]=std::numeric_limits<float>::quiet_NaN();
    assert(!game_fvf_clipped_point_vertices(
        eyeCrossing,nullptr,3u,4u,1u,0u,64u,lerp,eyePoints));
    assert(eyePoints.size()==validEyePoints.size());

}
