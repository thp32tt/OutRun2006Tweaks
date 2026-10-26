// 01087: authentic indexed SM3 fan center/rim across bounded GPU windows.
#include "live_game_sm3_stream_assembly.hpp"
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
    std::vector<std::uint8_t> unchanged{42u};
    assert(!game_sm3_assemble_indexed_fan_window(
        decl,streams,invalid.data(),invalid.size(),13u,4u,unchanged));
    assert(unchanged==std::vector<std::uint8_t>{42u});
    assert(!game_sm3_copy_native_indexed_fan_window(
        streams[0].data,stride,sourceVertices,invalid.data(),invalid.size(),
        13u,4u,unchanged));
    assert(unchanged==std::vector<std::uint8_t>{42u});
    assert(!game_sm3_plan_native_indexed_fan_chunks(
        sourceVertices,ib.size(),32u,64u,256u,18u,2u,4096u).chunkCount);
    assert(!game_sm3_plan_native_indexed_fan_chunks(
        sourceVertices,ib.size(),32u,64u,256u,18u,8u,400u).chunkCount);
    assert(!game_sm3_plan_native_indexed_fan_chunks(
        sourceVertices,ib.size(),32u,64u,2048u,90u,8u,4096u).chunkCount);
    // Nonindexed oversized fan index expansion also remains streamable.
    assert(game_sm3_plan_native_fan_chunks(17u,12u,64u,2048u,18u,8u).chunkCount==3u);
    return 0;
}
