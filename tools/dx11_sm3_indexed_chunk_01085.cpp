// 01085: source-authored indexed triangles/lines -> packed native Draw.
#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::uint32_t vertices=15u, stride=32u;
    const std::array<std::uint32_t,18> indices{{
        0u,3u,6u,6u,3u,9u,9u,12u,14u,14u,12u,1u,1u,6u,7u,7u,9u,0u}};
    const auto plan=game_sm3_plan_native_indexed_chunks(
        4u,vertices,indices.size(),stride,64u,192u,8u,4096u);
    assert(plan.verticesPerChunk==6u && plan.chunkCount==3u);
    for (auto type : {3u,5u,6u,7u})
        assert(!game_sm3_plan_native_indexed_chunks(
            type,vertices,indices.size(),stride,64u,192u,8u,4096u).chunkCount);
    assert(!game_sm3_plan_native_indexed_chunks(
        4u,vertices,indices.size()-1u,stride,64u,192u,8u,4096u).chunkCount);
    assert(!game_sm3_plan_native_indexed_chunks(
        4u,vertices,indices.size(),stride,64u,192u,8u,512u).chunkCount);
    assert(!game_sm3_plan_native_indexed_chunks(
        4u,vertices,indices.size(),stride,64u,192u,2u,4096u).chunkCount);
    assert(!game_sm3_plan_native_indexed_chunks(
        4u,4u,indices.size(),stride,64u,192u,8u,4096u).chunkCount);
    assert(game_sm3_plan_native_indexed_chunks(
        4u,vertices,3u,stride,64u,192u,8u,4096u).chunkCount==1u);
    std::array<float,vertices*3u> xyz{};
    std::array<float,vertices*2u> uv{};
    for(std::uint32_t i=0u;i<vertices;++i) {
        xyz[i*3u]=float(i); uv[i*2u]=float(i)/17.f;
    }
    std::array<GameSm3StreamView,16> streams{};
    streams[0]={reinterpret_cast<const std::uint8_t*>(xyz.data()),12u,vertices};
    streams[1]={reinterpret_cast<const std::uint8_t*>(uv.data()),8u,vertices};
    const std::vector<GameSm3ElementRef> decl{{0u,0u,2u},{1u,0u,1u}};
    std::vector<std::uint8_t> chunk, all;
    for(std::uint32_t n=0u;n<plan.chunkCount;++n) {
        const auto first=n*plan.verticesPerChunk;
        const auto count=(std::min)(plan.verticesPerChunk,
                                    std::uint32_t(indices.size())-first);
        assert(count%3u==0u);
        assert(game_sm3_assemble_indexed_window(
            decl,streams,indices.data(),indices.size(),first,count,chunk));
        for(std::uint32_t i=0u;i<count;++i) {
            float p=0.f,t=0.f;
            std::memcpy(&p,chunk.data()+i*stride,4u);
            std::memcpy(&t,chunk.data()+i*stride+16u,4u);
            assert(p==float(indices[first+i]));
            assert(t==uv[indices[first+i]*2u]);
        }
        all.insert(all.end(),chunk.begin(),chunk.end());
    }
    assert(all.size()==indices.size()*stride);
    auto saved=chunk;
    auto bad=indices; bad[12]=vertices;
    assert(!game_sm3_assemble_indexed_window(
        decl,streams,bad.data(),bad.size(),12u,6u,chunk));
    assert(chunk==saved);
    assert(!game_sm3_assemble_indexed_window(
        decl,streams,indices.data(),indices.size(),17u,3u,chunk));
    assert(chunk==saved);
}
