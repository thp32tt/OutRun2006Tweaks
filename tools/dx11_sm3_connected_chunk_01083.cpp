// OutRun game-authored SM3 LINESTRIP/TRIANGLESTRIP native GPU upload windows.
#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    for (std::uint32_t type : {3u, 5u}) {
        const auto plan = game_sm3_plan_native_connected_chunks(
            type, false, 17u, 32u, 8u, 8u * 32u, 8u);
        assert(plan.verticesPerChunk == (type == 3u ? 8u : 8u));
        assert(plan.advanceVertices == (type == 3u ? 7u : 6u));
        const std::uint32_t group = type == 3u ? 2u : 3u;
        std::vector<std::array<std::uint32_t,3>> expected, actual;
        const auto append = [&](std::vector<std::array<std::uint32_t,3>>& out,
                                std::uint32_t first, std::uint32_t count) {
            for (std::uint32_t v=0; v+group<=count; ++v) {
                if (group==2u) out.push_back({first+v, first+v+1u, 0u});
                else if (v%2u==0u)
                    out.push_back({first+v,first+v+1u,first+v+2u});
                else out.push_back({first+v+1u,first+v,first+v+2u});
            }
        };
        append(expected,0u,17u);
        for (std::uint32_t chunk=0; chunk<plan.chunkCount; ++chunk) {
            const auto first=chunk*plan.advanceVertices;
            const auto count=(std::min)(plan.verticesPerChunk,17u-first);
            assert(first% (type==3u ? 1u : 2u)==0u);
            assert(count>=group && count<=plan.verticesPerChunk);
            append(actual,first,count);
        }
        assert(actual==expected);
        assert(!game_sm3_plan_native_connected_chunks(
            type,true,17u,32u,8u,256u,8u).chunkCount);
        assert(!game_sm3_plan_native_connected_chunks(
            type,false,17u,32u,8u,256u,2u).chunkCount);
    }
    // Reject unknown fans/lists, buffers without enough seam+triangle space,
    // and already-fitting originals (which remain one native Draw).
    for (auto type : {1u,2u,4u,6u,7u})
        assert(!game_sm3_plan_native_connected_chunks(
            type,false,17u,32u,8u,256u,8u).chunkCount);
    assert(!game_sm3_plan_native_connected_chunks(
        5u,false,10u,32u,8u,96u,8u).chunkCount);
    assert(!game_sm3_plan_native_connected_chunks(
        3u,false,3u,32u,8u,256u,8u).chunkCount);
    // Exact stream windows include ORIGINAL seam vertex attributes.
    std::array<std::uint8_t,17u*12u> positions{};
    std::array<std::uint8_t,17u*8u> texcoords{};
    for (std::uint32_t v=0u;v<17u;++v) {
        const float p[3]={float(v),float(v)+1.f,float(v)+2.f};
        const float uv[2]={float(v)/17.f,float(v)/19.f};
        std::memcpy(positions.data()+v*12u,p,sizeof(p));
        std::memcpy(texcoords.data()+v*8u,uv,sizeof(uv));
    }
    const std::vector<GameSm3ElementRef> attributes{{0u,0u,2u},{1u,0u,1u}};
    std::array<GameSm3StreamView,16> streams{};
    streams[0]={positions.data(),12u,17u};
    streams[1]={texcoords.data(),8u,17u};
    std::vector<std::uint8_t> entire, part, beforeFailure;
    assert(game_sm3_assemble_streams(attributes,streams,17u,entire));
    const auto plan=game_sm3_plan_native_connected_chunks(
        5u,false,17u,32u,8u,256u,8u);
    for (std::uint32_t chunk=0;chunk<plan.chunkCount;++chunk) {
        const auto first=chunk*plan.advanceVertices;
        const auto count=(std::min)(plan.verticesPerChunk,17u-first);
        assert(game_sm3_assemble_streams(attributes,streams,count,part,first));
        assert(std::memcmp(part.data(),entire.data()+first*32u,
                           count*32u)==0);
    }
    beforeFailure=part;
    assert(!game_sm3_assemble_streams(
        attributes,streams,6u,part,16u));
    assert(part==beforeFailure); // no partial failed seam upload
}
