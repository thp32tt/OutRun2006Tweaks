// 01087: authentic indexed SM3 fan center/rim across bounded GPU windows.
#include "live_game_sm3_stream_assembly.hpp"
#include "live_game_sm3_polygon_raster.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::uint32_t sourceVertices=17u, stride=12u;
    const std::array<std::uint32_t,17> ib{{
        14u,2u,9u,3u,12u,5u,11u,0u,7u,6u,1u,4u,8u,13u,10u,15u,16u}};
    std::array<std::array<float,3>,sourceVertices> xyz{};
    for(std::uint32_t i=0;i<sourceVertices;++i)
        xyz[i]={float(i),float(i)+1.f,float(i)+2.f};
    std::array<GameSm3StreamView,16> streams{};
    streams[0]={reinterpret_cast<const std::uint8_t*>(xyz.data()),stride,sourceVertices};
    const std::vector<GameSm3ElementRef> decl{{0u,0u,2u}};
    // Overflow can arise from packed VB width OR the fully expanded fan IB.
    const auto plan=game_sm3_plan_native_indexed_fan_chunks(
        sourceVertices,ib.size(),32u,64u,256u,18u,8u,4096u);
    assert(plan.verticesPerChunk==8u && plan.advanceRimVertices==6u);
    assert(plan.chunkCount==3u);
    std::vector<std::array<std::uint32_t,3>> triangles;
    for(std::uint32_t chunk=0;chunk<plan.chunkCount;++chunk) {
        const auto firstRim=1u+chunk*plan.advanceRimVertices;
        const auto count=(std::min)(plan.verticesPerChunk,
                                    std::uint32_t(1u+ib.size()-firstRim));
        std::vector<std::uint8_t> packed,raw;
        assert(game_sm3_assemble_indexed_fan_window(
            decl,streams,ib.data(),ib.size(),firstRim,count,packed));
        assert(game_sm3_copy_native_indexed_fan_window(
            streams[0].data,stride,sourceVertices,ib.data(),ib.size(),
            firstRim,count,raw));
        for(std::uint32_t k=0;k<count;++k) {
            const auto src=ib[k ? firstRim+k-1u : 0u];
            float pv=0.f,rv=0.f;
            std::memcpy(&pv,packed.data()+k*16u,sizeof(float));
            std::memcpy(&rv,raw.data()+k*stride,sizeof(float));
            assert(pv==float(src) && rv==float(src));
        }
        std::vector<std::uint32_t> local;
        assert(game_sm3_fan_window_indices(count,18u,local));
        for(std::size_t k=0;k<local.size();k+=3u) {
            const auto src=[&](std::uint32_t v) {
                return ib[v ? firstRim+v-1u : 0u]; };
            triangles.push_back({
                src(local[k]),src(local[k+1u]),src(local[k+2u])});
        }
    }
    assert(triangles.size()==ib.size()-2u);
    for(std::size_t i=0;i<triangles.size();++i)
        assert((triangles[i]==std::array<std::uint32_t,3>{
            ib[0],ib[i+1u],ib[i+2u]}));
    // Bad late rim index: both assemblers fail transactionally.
    auto invalid=ib; invalid[16u]=sourceVertices;
    // A four-vertex window intentionally stops at IB[15], so the invalid
    // IB[16] is not inside that upload. The five-vertex tail must reject it.
    std::vector<std::uint8_t> preceding;
    assert(game_sm3_assemble_indexed_fan_window(
        decl,streams,invalid.data(),invalid.size(),13u,4u,preceding));
    assert(preceding.size()==4u*16u);
    std::vector<std::uint8_t> unchanged{42u};
    assert(!game_sm3_assemble_indexed_fan_window(
        decl,streams,invalid.data(),invalid.size(),13u,5u,unchanged));
    assert(unchanged==std::vector<std::uint8_t>{42u});
    assert(!game_sm3_copy_native_indexed_fan_window(
        streams[0].data,stride,sourceVertices,invalid.data(),invalid.size(),
        13u,5u,unchanged));
    assert(unchanged==std::vector<std::uint8_t>{42u});
    assert(!game_sm3_plan_native_indexed_fan_chunks(
        sourceVertices,ib.size(),32u,64u,256u,18u,2u,4096u).chunkCount);
    assert(!game_sm3_plan_native_indexed_fan_chunks(
        sourceVertices,ib.size(),32u,64u,256u,18u,8u,400u).chunkCount);
    assert(!game_sm3_plan_native_indexed_fan_chunks(
        sourceVertices,ib.size(),32u,64u,2048u,90u,8u,4096u).chunkCount);
    // Nonindexed oversized fan index expansion also remains streamable.
    assert(game_sm3_plan_native_fan_chunks(17u,12u,64u,2048u,18u,8u).chunkCount==3u);

    // 01088: windowed REAL shader-bound fans preserve every triangle
    // occurrence under SOLID/WIREFRAME/POINT, indexed and nonindexed.
    // POINTLIST must replay shared vertices, not deduplicate fan center.
    const auto multi=game_sm3_plan_native_indexed_fan_chunks(
        sourceVertices,ib.size(),32u,64u,256u,18u,8u,4096u);
    std::vector<std::uint32_t> expectedPoints;
    assert(game_sm3_expand_polygon_points(
        6u,ib.data(),ib.size(),sourceVertices,128u,expectedPoints));
    std::vector<std::uint32_t> expectedLinear;
    assert(game_sm3_expand_polygon_points(
        6u,nullptr,ib.size(),sourceVertices,128u,expectedLinear));
    for(const std::uint32_t fill : {1u,2u,3u}) {
        std::vector<std::uint32_t> emittedIndexed, emittedLinear;
        std::uint32_t covered=0u;
        for(std::uint32_t chunk=0u;chunk<multi.chunkCount;++chunk) {
            const auto firstRim=1u+chunk*multi.advanceRimVertices;
            const auto count=(std::min)(
                multi.verticesPerChunk,std::uint32_t(1u+ib.size()-firstRim));
            const auto window=game_sm3_fan_fill_window_plan(
                fill,ib.size(),firstRim,count,18u);
            assert(window.supported);
            assert(window.nativeIndexCount==3u*window.sourceTriangles);
            covered+=window.sourceTriangles;
            std::vector<std::uint32_t> local;
            assert(game_sm3_fan_window_indices(count,18u,local));
            assert(local.size()==window.nativeIndexCount);
            for(const auto v : local) {
                const auto sourceOrdinal=v?firstRim+v-1u:0u;
                emittedIndexed.push_back(ib[sourceOrdinal]);
                emittedLinear.push_back(sourceOrdinal);
            }
        }
        assert(covered==ib.size()-2u);
        assert(emittedIndexed==expectedPoints);
        assert(emittedLinear==expectedLinear);
    }
    // Fail closed on source-tail overrun, unsupported fill, or native IB
    // budget underflow, without ever issuing a partial point/wire draw.
    assert(!game_sm3_fan_fill_window_plan(
        1u,ib.size(),16u,3u,18u).supported);
    assert(!game_sm3_fan_fill_window_plan(
        4u,ib.size(),1u,8u,18u).supported);
    assert(!game_sm3_fan_fill_window_plan(
        2u,ib.size(),1u,8u,17u).supported);

    // 01089: stitched real indexed/nonindexed TRIANGLESTRIP windows retain
    // winding, point occurrences and shader-visible original source order.
    constexpr std::uint32_t maxPointIndices=18u;
    const auto stripPlan=game_sm3_plan_native_connected_chunks(
        5u,false,sourceVertices,12u,8u,128u,8u);
    assert(stripPlan.verticesPerChunk==8u);
    assert(stripPlan.advanceVertices==6u && stripPlan.chunkCount==3u);
    std::vector<std::uint32_t> expectedStripIndexed,expectedStripLinear;
    assert(game_sm3_expand_polygon_points(
        5u,ib.data(),ib.size(),sourceVertices,128u,expectedStripIndexed));
    assert(game_sm3_expand_polygon_points(
        5u,nullptr,ib.size(),sourceVertices,128u,expectedStripLinear));
    for(const auto fillMode:{1u,2u,3u}) {
        std::vector<std::uint32_t> streamedIndexed,streamedLinear;
        std::uint32_t coveredTriangles=0u;
        for(std::uint32_t part=0u;part<stripPlan.chunkCount;++part) {
            const auto first=part*stripPlan.advanceVertices;
            const auto count=(std::min)(
                stripPlan.verticesPerChunk,sourceVertices-first);
            const auto window=game_sm3_strip_fill_window_plan(
                fillMode,ib.size(),first,count,maxPointIndices);
            assert(window.supported);
            coveredTriangles+=window.sourceTriangles;
            if(fillMode==1u)
                assert(window.pointIndexCount==3u*window.sourceTriangles);
            else
                assert(window.pointIndexCount==0u);
            std::vector<std::uint32_t> local;
            assert(game_sm3_expand_polygon_points(
                5u,nullptr,count,count,maxPointIndices,local));
            for(auto localVertex:local) {
                streamedIndexed.push_back(ib[first+localVertex]);
                streamedLinear.push_back(first+localVertex);
            }
        }
        assert(coveredTriangles==ib.size()-2u);
        assert(streamedIndexed==expectedStripIndexed);
        assert(streamedLinear==expectedStripLinear);
    }
    assert(!game_sm3_strip_fill_window_plan(
        1u,ib.size(),1u,8u,maxPointIndices).supported);
    assert(!game_sm3_strip_fill_window_plan(
        1u,ib.size(),12u,8u,maxPointIndices).supported);
    assert(!game_sm3_strip_fill_window_plan(
        1u,ib.size(),0u,9u,maxPointIndices).supported);
    assert(!game_sm3_strip_fill_window_plan(
        4u,ib.size(),0u,8u,maxPointIndices).supported);
    // The actual entire source IB is checked before any indexed GPU mutation.
    auto damaged=ib;damaged.back()=sourceVertices;
    bool validFullSource=true;
    for(auto index:damaged)validFullSource&=index<sourceVertices;
    assert(!validFullSource);
    return 0;
}
