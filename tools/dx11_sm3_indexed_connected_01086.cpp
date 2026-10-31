// 01086: source-authored connected indexed geometry -> native GPU windows.
#include "live_game_sm3_stream_assembly.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::uint32_t vertices=15u, stride=32u;
    const std::array<std::uint32_t,15> indices{{
        9u,1u,8u,2u,7u,3u,6u,4u,5u,0u,10u,11u,14u,12u,13u}};
    std::array<float,vertices*3u> xyz{};
    std::array<float,vertices*2u> uv{};
    for(std::uint32_t i=0u;i<vertices;++i) {
        xyz[i*3u]=float(i); uv[i*2u]=float(i)/17.f;
    }
    std::array<GameSm3StreamView,16> streams{};
    streams[0]={reinterpret_cast<const std::uint8_t*>(xyz.data()),12u,vertices};
    streams[1]={reinterpret_cast<const std::uint8_t*>(uv.data()),8u,vertices};
    const std::vector<GameSm3ElementRef> decl{{0u,0u,2u},{1u,0u,1u}};
    for(auto primitive : {3u,5u}) {
        const auto plan=game_sm3_plan_native_indexed_connected_chunks(
            primitive,vertices,indices.size(),stride,64u,192u,8u,4096u);
        assert(plan.verticesPerChunk==6u);
        assert(plan.advanceVertices==(primitive==3u ? 5u : 4u));
        assert(plan.chunkCount==(primitive==3u ? 3u : 4u));
        std::vector<std::uint32_t> expected, emitted;
        for(std::uint32_t i=0u;i+(primitive==3u ? 1u : 2u)<indices.size();++i) {
            if(primitive==3u) {
                expected.insert(expected.end(),{indices[i],indices[i+1u]});
            }else{
                expected.insert(expected.end(),{
                    indices[i+(i&1u)],indices[i+((i&1u) ? 0u : 1u)],
                    indices[i+2u]});
            }
        }
        std::vector<std::uint8_t> window;
        for(std::uint32_t chunk=0u;chunk<plan.chunkCount;++chunk) {
            const auto first=chunk*plan.advanceVertices;
            const auto count=(std::min)(plan.verticesPerChunk,
                std::uint32_t(indices.size())-first);
            assert(primitive!=5u || first%2u==0u);
            assert(game_sm3_assemble_indexed_window(
                decl,streams,indices.data(),indices.size(),first,count,window));
            for(std::uint32_t v=0u;v<count;++v) {
                float position=-1.f, tex=-1.f;
                std::memcpy(&position,window.data()+v*stride,4u);
                std::memcpy(&tex,window.data()+v*stride+16u,4u);
                assert(position==float(indices[first+v]));
                assert(tex==uv[indices[first+v]*2u]);
            }
            for(std::uint32_t i=0u;i+(primitive==3u ? 1u : 2u)<count;++i) {
                if(primitive==3u) {
                    emitted.insert(emitted.end(),
                        {indices[first+i],indices[first+i+1u]});
                }else {
                    emitted.insert(emitted.end(),{
                        indices[first+i+(i&1u)],
                        indices[first+i+((i&1u) ? 0u : 1u)],
                        indices[first+i+2u]});
                }
            }
        }
        assert(emitted==expected); // line coverage and triangle winding
        const auto saved=window;
        auto bad=indices;bad[12u]=vertices;
        assert(!game_sm3_assemble_indexed_window(
            decl,streams,bad.data(),bad.size(),12u,3u,window));
        assert(window==saved);
    }
    assert(!game_sm3_plan_native_indexed_connected_chunks(
        4u,vertices,indices.size(),stride,64u,192u,8u,4096u).chunkCount);
    assert(!game_sm3_plan_native_indexed_connected_chunks(
        5u,vertices,indices.size(),stride,64u,192u,2u,4096u).chunkCount);
    assert(!game_sm3_plan_native_indexed_connected_chunks(
        5u,vertices,indices.size(),stride,64u,192u,8u,512u).chunkCount);
    assert(!game_sm3_plan_native_indexed_connected_chunks(
        5u,vertices,indices.size(),stride,64u,512u,8u,4096u).chunkCount);
    assert(!game_sm3_plan_native_indexed_connected_chunks(
        5u,vertices,indices.size(),stride,64u,64u,8u,4096u).chunkCount);
}
