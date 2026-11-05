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
    // 01245: Original indexed and non-indexed TRIANGLEFAN in D3DFILL_POINT.
    // The first source/index occurrence is reused for every source face;
    // unlike a strip, a fan never alternates winding. Point fill emits
    // THREE GPU points per surviving triangle, preserving the shared anchor.
    Vertex fan[]{
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f, .5f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.5f, .5f,.5f,1.f},{1,1,1,1,1,1}}
    };
    assert(build(fan,4u,nullptr,4u,6u,2u,0u,out));
    assert((out==std::vector<std::uint32_t>{0,1,2,0,2,3}));
    assert(build(fan,4u,nullptr,4u,6u,1u,0u,out));
    assert((out==std::vector<std::uint32_t>{0,1,2,0,2,3}));
    const std::uint32_t reversedFan[]{0u,3u,2u,1u};
    assert(build(fan,4u,reversedFan,4u,6u,3u,0u,out));
    assert((out==std::vector<std::uint32_t>{0,3,2,0,2,1}));
    // Indexed anchor is intentionally not vertex zero.
    const std::uint32_t movedAnchor[]{2u,3u,0u,1u};
    assert(build(fan,4u,movedAnchor,4u,6u,2u,0u,out));
    assert((out==std::vector<std::uint32_t>{2,3,0,2,0,1}));
    const auto safeFan=out;
    // A partly clipped later fan triangle requires new vertices; the fast
    // indexed plan must reject without publishing an incomplete Draw.
    fan[3].clip[0]=-2.f;
    assert(!build(fan,4u,movedAnchor,4u,6u,2u,0u,out));
    assert(out==safeFan);
    fan[3].clip[0]=-.5f;
    fan[3].clipDistances[0]=-1.f;
    assert(!build(fan,4u,movedAnchor,4u,6u,2u,1u,out));
    assert(out==safeFan);
    fan[3].clipDistances[0]=1.f;
    const std::uint32_t badFan[]{2u,3u,0u,99u};
    assert(!build(fan,4u,badFan,4u,6u,2u,0u,out));
    assert(out==safeFan);
    assert(!build(fan,4u,movedAnchor,4u,6u,2u,0u,out,5u));
    assert(out==safeFan);
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
    assert(clipped.size()==6u);
    // A clipped source triangle becomes two D3D11 point triangles, not
    // four de-duplicated points. The shared polygon fan corners retain
    // their exact interpolated original-game shader attributes.
    for (unsigned p=0u;p<4u;++p) {
        assert(clipped[0].clip[p]==clipped[3].clip[p]);
        assert(clipped[2].clip[p]==clipped[4].clip[p]);
        assert(clipped[0].clip0[p]==clipped[3].clip0[p]);
        assert(clipped[2].clip1[p]==clipped[4].clip1[p]);
    }
    for (unsigned p=0u;p<2u;++p) {
        assert(clipped[0].uv[p]==clipped[3].uv[p]);
        assert(clipped[2].uv[p]==clipped[4].uv[p]);
    }
    const auto clippedSix=clipped;
    assert(!game_fvf_clipped_point_vertices(
        source,nullptr,3u,4u,1u,0u,5u,lerp,clipped));
    assert(clipped.size()==clippedSix.size());
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
    // Valid D3D9 WVP camera-plane corner: the full polygon must clip to
    // positive-W GPU points rather than lose an authentic game source Draw.
    source[0].clip[3]=0.f;
    assert(game_fvf_clipped_point_vertices(
        source,nullptr,3u,4u,1u,0u,64u,lerp,clipped));
    assert(clipped.size()>=3u);
    for(const auto& v:clipped) assert(v.clip[3]>0.f);
    const auto cameraPlanePoints=clipped;
    // An all-zero homogeneous coordinate has no projectable direction;
    // failing that source leaves previous native IA points untouched.
    source[0].clip[0]=0.f;
    source[0].clip[1]=0.f;
    source[0].clip[2]=0.f;
    assert(!game_fvf_clipped_point_vertices(
        source,nullptr,3u,4u,1u,0u,64u,lerp,clipped));
    assert(clipped.size()==cameraPlanePoints.size());
    source[0].clip[0]=-.5f;
    source[0].clip[1]=-.5f;
    source[0].clip[2]=.5f;
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


    // 01244: source D3D9 FVF triangles with tiny but strictly positive W
    // already rasterize through native D3D11 and GPU RGB capture. The
    // POINT-fill lowering must not discard them via a fixed 1e-5 plane.
    Vertex tinyPositive[]{
        {{-5.e-8f,-5.e-8f,5.e-8f,1.e-7f},{1,1,1,1,1,1}},
        {{ 5.e-8f,-5.e-8f,5.e-8f,1.e-7f},{1,1,1,1,1,1}},
        {{-5.e-8f, 5.e-8f,5.e-8f,1.e-7f},{1,1,1,1,1,1}}
    };
    const std::uint32_t tinyIndexed[]{0u,1u,2u,2u,1u,0u};
    assert(build(tinyPositive,3u,tinyIndexed,6u,4u,1u,1u,out));
    assert((out==std::vector<std::uint32_t>{0,1,2,2,1,0}));
    assert(build(tinyPositive,3u,tinyIndexed,6u,4u,2u,1u,out));
    assert((out==std::vector<std::uint32_t>{0,1,2}));
    const auto savedTiny=out;
    tinyPositive[2].clip[3]=0.f; // crossing requires full point clip, not IA
    assert(!build(tinyPositive,3u,tinyIndexed,6u,4u,2u,1u,out));
    assert(out==savedTiny);
    tinyPositive[2].clip[3]=1.e-7f;
    tinyPositive[1].clipDistances[0]=std::numeric_limits<float>::quiet_NaN();
    assert(!build(tinyPositive,3u,tinyIndexed,6u,4u,2u,1u,out));
    assert(out==savedTiny);
    tinyPositive[1].clipDistances[0]=1.f;

    // The actual clipped-point VS attribute path must independently accept
    // the same positive-W source polygon and interpolate its real UV payload
    // when one corner crosses a regular homogeneous XY plane. User-plane
    // clipping still operates, and failed IA never mutates prior GPU points.
    std::vector<ClipVertex> tinyPointSource{
        {{-5.e-8f,-5.e-8f,5.e-8f,1.e-7f},{1,1,1,1},{1,1,0,0},{0,0}},
        {{ 5.e-8f,-5.e-8f,5.e-8f,1.e-7f},{1,1,1,1},{1,1,0,0},{1,0}},
        {{-5.e-8f, 5.e-8f,5.e-8f,1.e-7f},{1,1,1,1},{1,1,0,0},{0,1}}
    };
    std::vector<ClipVertex> tinyPointDest;
    assert(game_fvf_clipped_point_vertices(
        tinyPointSource,nullptr,3u,4u,1u,1u,64u,lerp,tinyPointDest));
    assert(tinyPointDest.size()==3u);
    for (const auto& v:tinyPointDest) {
        assert(v.clip[3]>0.f && v.clip[3]<1.e-5f);
        assert(v.clip0[0]>=0.f && v.uv[0]>=0.f && v.uv[0]<=1.f);
    }
    tinyPointSource[1].clip[0]=2.e-7f; // regular X homogeneous clip
    assert(game_fvf_clipped_point_vertices(
        tinyPointSource,nullptr,3u,4u,1u,1u,64u,lerp,tinyPointDest));
    assert(tinyPointDest.size()==6u);
    assert(tinyPointDest[0].clip[3]==tinyPointDest[3].clip[3]);
    assert(tinyPointDest[2].uv[0]==tinyPointDest[4].uv[0]);
    for (const auto& v:tinyPointDest) {
        assert(v.clip[3]>0.f && v.clip[3]<1.e-5f);
        assert(v.clip[0]<=v.clip[3]+1.e-12f);
    }
    const auto savedTinyPoints=tinyPointDest;
    for (auto& v:tinyPointSource) v.clip0[0]=-1.f;
    assert(!game_fvf_clipped_point_vertices(
        tinyPointSource,nullptr,3u,4u,1u,1u,64u,lerp,tinyPointDest));
    assert(tinyPointDest.size()==savedTinyPoints.size());
    for (auto& v:tinyPointSource) v.clip0[0]=1.f;
    for (unsigned p=0u;p<4u;++p) tinyPointSource[0].clip[p]=0.f;
    assert(!game_fvf_clipped_point_vertices(
        tinyPointSource,nullptr,3u,4u,1u,1u,64u,lerp,tinyPointDest));
    assert(tinyPointDest.size()==savedTinyPoints.size());

    // 01247: tiny original FVF positive-W vertices can be visible in a
    // camera-plane-crossing triangle. An absolute W>=1e-5 clip erroneously
    // discards EVERY source corner even though two valid corners rasterize.
    // Keep both texture stages and the enabled user clip plane after actual
    // homogeneous clipping, and do not mutate an earlier native point plan
    // when a later indexed game source triangle is malformed.
    std::vector<ClipVertex> nearEyeTiny{
        {{-5.e-8f,-5.e-8f,2.e-8f,1.e-7f},{1,1,1,1},{1,1,0,0},{0,0}},
        {{ 5.e-8f,-5.e-8f,2.e-8f,1.e-7f},{1,1,1,1},{1,1,0,0},{1,0}},
        {{ 0.f,   0.f,-2.e-8f,-1.e-7f},{1,1,1,1},{1,1,0,0},{.5f,1}}
    };
    std::vector<ClipVertex> nearEyeOut;
    assert(game_fvf_clipped_point_vertices(
        nearEyeTiny,nullptr,3u,4u,1u,1u,64u,lerp,nearEyeOut));
    assert(nearEyeOut.size()>=3u && nearEyeOut.size()%3u==0u);
    for (const auto& v : nearEyeOut) {
        assert(v.clip[3]>0.f && v.clip[3]<1.e-5f);
        assert(v.clip[0]>=-v.clip[3]-1.e-12f &&
               v.clip[0]<= v.clip[3]+1.e-12f);
        assert(v.clip[1]>=-v.clip[3]-1.e-12f &&
               v.clip[1]<= v.clip[3]+1.e-12f);
        assert(v.clip0[0]>=-1.e-6f);
        assert(v.uv[0]>=0.f && v.uv[0]<=1.f &&
               v.uv[1]>=0.f && v.uv[1]<=1.f);
    }
    const auto nearEyeGood=nearEyeOut;
    const std::uint32_t invalidNearEye[]{0u,1u,99u};
    assert(!game_fvf_clipped_point_vertices(
        nearEyeTiny,invalidNearEye,3u,4u,1u,1u,64u,lerp,nearEyeOut));
    assert(nearEyeOut.size()==nearEyeGood.size());
    for (auto& v : nearEyeTiny) v.clip[3]=-1.e-7f;
    assert(!game_fvf_clipped_point_vertices(
        nearEyeTiny,nullptr,3u,4u,1u,1u,64u,lerp,nearEyeOut));
    assert(nearEyeOut.size()==nearEyeGood.size());
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

    // 01245: The same TRIANGLEFAN must reach native clipped POINT vertices
    // when an original fan face intersects XY/user/eye planes. The CPU
    // interpolation preserves the real game UVs; the GPU path still owns
    // the pixel, while malformed later IB entries leave the old plan intact.
    std::vector<ClipVertex> fanSource{
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1},{1,1,0,0},{0,0}},
        {{ .5f,-.5f,.5f,1.f},{1,1,1,1},{1,1,0,0},{1,0}},
        {{ .5f, .5f,.5f,1.f},{1,1,1,1},{1,1,0,0},{1,1}},
        {{-.5f, .5f,.5f,1.f},{1,1,1,1},{1,1,0,0},{0,1}}
    };
    std::vector<ClipVertex> fanPoints;
    assert(game_fvf_clipped_point_vertices(
        fanSource,nullptr,4u,6u,2u,0u,64u,lerp,fanPoints));
    assert(fanPoints.size()==6u);
    assert(game_fvf_clipped_point_vertices(
        fanSource,reversedFan,4u,6u,3u,0u,64u,lerp,fanPoints));
    assert(fanPoints.size()==6u);
    assert(game_fvf_clipped_point_vertices(
        fanSource,movedAnchor,4u,6u,2u,0u,64u,lerp,fanPoints));
    assert(fanPoints.size()==6u);
    fanSource[3].clip[0]=-2.f; // second triangle crosses real XY plane
    assert(game_fvf_clipped_point_vertices(
        fanSource,movedAnchor,4u,6u,2u,0u,64u,lerp,fanPoints));
    assert(fanPoints.size()==9u); // clipped face: 6, surviving face: 3
    assert(fanPoints.size()%3u==0u);
    for(const auto& v:fanPoints) {
        assert(v.clip[0]>=-v.clip[3]-1.e-5f);
        assert(v.uv[0]>=0.f && v.uv[0]<=1.f);
        assert(v.uv[1]>=0.f && v.uv[1]<=1.f);
    }
    fanSource[3].clip[0]=-.5f;
    fanSource[3].clip0[0]=-1.f; // original enabled user plane
    assert(game_fvf_clipped_point_vertices(
        fanSource,movedAnchor,4u,6u,2u,1u,64u,lerp,fanPoints));
    for(const auto& v:fanPoints) assert(v.clip0[0]>=-1.e-5f);
    fanSource[3].clip0[0]=1.f;
    fanSource[3].clip[3]=-.2f; // real D3D9 perspective eye crossing
    assert(game_fvf_clipped_point_vertices(
        fanSource,movedAnchor,4u,6u,1u,0u,64u,lerp,fanPoints));
    for(const auto& v:fanPoints) assert(v.clip[3]>0.f);
    const auto savedFanPoints=fanPoints;
    const std::uint32_t lateBadFan[]{2u,3u,0u,99u};
    assert(!game_fvf_clipped_point_vertices(
        fanSource,lateBadFan,4u,6u,1u,0u,64u,lerp,fanPoints));
    assert(fanPoints.size()==savedFanPoints.size());
    assert(!game_fvf_clipped_point_vertices(
        fanSource,movedAnchor,4u,6u,1u,0u,2u,lerp,fanPoints));
    assert(fanPoints.size()==savedFanPoints.size());
    fanSource[3].clip[3]=std::numeric_limits<float>::quiet_NaN();
    assert(!game_fvf_clipped_point_vertices(
        fanSource,movedAnchor,4u,6u,1u,0u,64u,lerp,fanPoints));
    assert(fanPoints.size()==savedFanPoints.size());

    // 01248: D3DFILL_POINT emits real vertices even for a triangle whose
    // projected area is much smaller than the old fixed 1e-12 cutoff.
    // This must work through BOTH the indexed fast path and the CPU-clipped
    // Draw-to-native-POINTLIST path, preserving safe culling and fallback.
    Vertex hairline[]{ 
        {{-.5f,0.f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f,0.f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .5f,1.e-13f,.5f,1.f},{1,1,1,1,1,1}}
    };
    const std::uint32_t hairIndices[]{0u,1u,2u};
    assert(build(hairline,3u,hairIndices,3u,4u,1u,0u,out));
    assert((out==std::vector<std::uint32_t>{0u,1u,2u}));
    assert(build(hairline,3u,nullptr,3u,4u,2u,0u,out));
    const auto goodHair=out;
    assert(!build(hairline,3u,nullptr,3u,4u,3u,0u,out));
    assert(out==goodHair); // cull must not publish partial GPU geometry
    hairline[2].clip[1]=0.f;
    assert(!build(hairline,3u,nullptr,3u,4u,1u,0u,out));
    assert(out==goodHair);
    hairline[2].clip[1]=1.e-13f;

    // Crossing a native homogeneous X clip plane creates four true D3D9
    // polygon corners and hence SIX GPU point occurrences (two triangles).
    // Their signed area is also below the old 2e-12 fixed cutoff.
    std::vector<ClipVertex> thinClippedSource{
        {{-.5f,0.f,.5f,1.f},{1,1,1,1},{1,1,0,0},{0,0}},
        {{1.5f,0.f,.5f,1.f},{1,1,1,1},{1,1,0,0},{1,0}},
        {{ .5f,1.e-13f,.5f,1.f},{1,1,1,1},{1,1,0,0},{.5f,1}}
    };
    std::vector<ClipVertex> thinNativePoints;
    assert(game_fvf_clipped_point_vertices(
        thinClippedSource,nullptr,3u,4u,1u,1u,64u,lerp,
        thinNativePoints));
    assert(thinNativePoints.size()==6u);
    for (const auto& v:thinNativePoints) {
        assert(v.clip[3]>0.f && v.clip[0]<=v.clip[3]);
        assert(v.clip[1]>=0.f && v.clip[1]<=1.e-13f);
        assert(v.clip0[0]>=0.f);
        assert(v.uv[0]>=0.f && v.uv[0]<=1.f);
        assert(v.uv[1]>=0.f && v.uv[1]<=1.f);
    }
    const auto savedThinPoints=thinNativePoints;
    assert(!game_fvf_clipped_point_vertices(
        thinClippedSource,nullptr,3u,4u,3u,1u,64u,lerp,
        thinNativePoints)); // authentic backface cull
    assert(thinNativePoints.size()==savedThinPoints.size());
    const std::uint32_t invalidThinIndices[]{0u,1u,99u};
    assert(!game_fvf_clipped_point_vertices(
        thinClippedSource,invalidThinIndices,3u,4u,1u,1u,64u,lerp,
        thinNativePoints));
    assert(thinNativePoints.size()==savedThinPoints.size());
    assert(!game_fvf_clipped_point_vertices(
        thinClippedSource,nullptr,3u,4u,1u,1u,5u,lerp,
        thinNativePoints)); // fail closed when native upload cannot fit
    assert(thinNativePoints.size()==savedThinPoints.size());
    // 01249: Actual native POINTLIST uses FLOAT SV_ClipDistance, not the
    // double clipping accumulator. For .1f -> -.3f intersections the old
    // floating interpolation can produce a tiny NEGATIVE signed distance,
    // culling an otherwise valid menu/vehicle/race point on the GPU.
    // Preserve source-authentic UV/color payload and snap generated user
    // clip intersections to exactly zero on BOTH hardware clip registers.
    std::vector<ClipVertex> roundedUserSource{
        {{-.5f,-.5f,.5f,1.f},{.1f,1,1,1},{.3f,1,0,0},{0,0}},
        {{ .5f,-.5f,.5f,1.f},{-.3f,1,1,1},{-.1f,1,0,0},{1,0}},
        {{-.5f, .5f,.5f,1.f},{.1f,1,1,1},{.3f,1,0,0},{0,1}}
    };
    std::vector<ClipVertex> roundedUserPoints;
    assert(game_fvf_clipped_point_vertices(
        roundedUserSource,nullptr,3u,4u,1u,1u,64u,lerp,
        roundedUserPoints));
    assert(roundedUserPoints.size()==6u);
    std::size_t snapped0=0u;
    for(const auto& v:roundedUserPoints) {
        assert(v.clip0[0]>=0.0f);
        snapped0+=v.clip0[0]==0.0f;
        assert(v.uv[0]>=0.0f && v.uv[0]<=1.0f);
        assert(v.uv[1]>=0.0f && v.uv[1]<=1.0f);
    }
    assert(snapped0>=2u);
    assert(game_fvf_clipped_point_vertices(
        roundedUserSource,nullptr,3u,4u,1u,16u,64u,lerp,
        roundedUserPoints));
    assert(roundedUserPoints.size()==6u);
    std::size_t snapped4=0u;
    for(const auto& v:roundedUserPoints) {
        assert(v.clip1[0]>=0.0f);
        snapped4+=v.clip1[0]==0.0f;
        assert(v.uv[0]>=0.0f && v.uv[0]<=1.0f);
    }
    assert(snapped4>=2u);
    // Hardware homogeneous X/Y/Z intersection vertices must likewise
    // sit ON the native float clip boundary before GPU submission.
    roundedUserSource[1].clip[0]=2.f;
    assert(game_fvf_clipped_point_vertices(
        roundedUserSource,nullptr,3u,4u,1u,0u,64u,lerp,
        roundedUserPoints));
    assert(roundedUserPoints.size()==6u);
    std::size_t rightBoundary=0u;
    for(const auto& v:roundedUserPoints) {
        assert(v.clip[0]<=v.clip[3]);
        rightBoundary+=v.clip[0]==v.clip[3];
        assert(v.uv[0]>=0.0f && v.uv[0]<=1.0f);
    }
    assert(rightBoundary>=2u);
    const auto stableRounded=roundedUserPoints;
    const std::uint32_t invalidRounded[]{0u,1u,99u};
    assert(!game_fvf_clipped_point_vertices(
        roundedUserSource,invalidRounded,3u,4u,1u,0u,64u,lerp,
        roundedUserPoints));
    assert(roundedUserPoints.size()==stableRounded.size());
    assert(!game_fvf_clipped_point_vertices(
        roundedUserSource,nullptr,3u,4u,1u,0u,5u,lerp,
        roundedUserPoints));
    assert(roundedUserPoints.size()==stableRounded.size());

    // 01250: A real FVF point-filled source face can cross the native
    // homogeneous right plane AND both enabled user clip-distance registers.
    // The CPU clip polygon is double precision; every generated float
    // vertex ultimately reaches D3D11 POINTLIST / SV_ClipDistance. A later
    // clipping intersection must not round back outside an earlier plane.
    std::vector<ClipVertex> multiPlaneSource{
        {{-.5f,-.5f,.5f,1.f},{.1f,1,1,1},{.3f,1,0,0},{0,0}},
        {{2.0f,-.5f,.5f,1.f},{.1f,1,1,1},{-.01f,1,0,0},{1,0}},
        {{-.5f, .5f,.5f,1.f},{-.3f,1,1,1},{.3f,1,0,0},{0,1}}
    };
    std::vector<ClipVertex> multiPlaneNative;
    assert(game_fvf_clipped_point_vertices(
        multiPlaneSource,nullptr,3u,4u,1u,17u,96u,lerp,multiPlaneNative));
    assert(multiPlaneNative.size()>=3u &&
           multiPlaneNative.size()%3u==0u);
    std::size_t rightEdgeCount=0u;
    std::size_t user0Count=0u, user4Count=0u;
    for (const auto& v:multiPlaneNative) {
        assert(v.clip[3]>0.f && std::isfinite(v.clip[3]));
        assert(v.clip[0]>=-v.clip[3] && v.clip[0]<=v.clip[3]);
        assert(v.clip[1]>=-v.clip[3] && v.clip[1]<=v.clip[3]);
        assert(v.clip[2]>=0.f && v.clip[2]<=v.clip[3]);
        assert(v.clip0[0]>=0.f && v.clip1[0]>=0.f);
        assert(v.uv[0]>=0.f && v.uv[0]<=1.f);
        assert(v.uv[1]>=0.f && v.uv[1]<=1.f);
        rightEdgeCount+=v.clip[0]==v.clip[3];
        user0Count+=v.clip0[0]==0.f;
        user4Count+=v.clip1[0]==0.f;
    }
    assert(rightEdgeCount>0u && user0Count>0u && user4Count>0u);
    const auto preservedMultiPlane=multiPlaneNative;
    const std::uint32_t lateBadMultiPlane[]{0u,1u,99u};
    assert(!game_fvf_clipped_point_vertices(
        multiPlaneSource,lateBadMultiPlane,3u,4u,1u,17u,96u,
        lerp,multiPlaneNative));
    assert(multiPlaneNative.size()==preservedMultiPlane.size());
    assert(!game_fvf_clipped_point_vertices(
        multiPlaneSource,nullptr,3u,4u,1u,17u,2u,
        lerp,multiPlaneNative));
    assert(multiPlaneNative.size()==preservedMultiPlane.size());
    multiPlaneSource[2].clip1[0]=
        std::numeric_limits<float>::quiet_NaN();
    assert(!game_fvf_clipped_point_vertices(
        multiPlaneSource,nullptr,3u,4u,1u,17u,96u,
        lerp,multiPlaneNative));
    assert(multiPlaneNative.size()==preservedMultiPlane.size());

    thinClippedSource[2].clip[1]=0.f;
    assert(!game_fvf_clipped_point_vertices(
        thinClippedSource,nullptr,3u,4u,1u,1u,64u,lerp,
        thinNativePoints)); // mathematically zero projected polygon
    assert(thinNativePoints.size()==savedThinPoints.size());

}
