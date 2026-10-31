// 01084: original D3D9 SM3 fan center, seam attributes and GPU triangle order.
#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::uint32_t total=17u, stride=12u;
    const auto plan=game_sm3_plan_native_fan_chunks(
        total,32u,8u,256u,100u,8u);
    assert(plan.verticesPerChunk==8u && plan.advanceRimVertices==6u);
    assert(plan.chunkCount==3u);
    std::vector<std::array<std::uint32_t,3>> actual;
    std::array<std::array<float,3>, total> vertices{};
    for (std::uint32_t v=0;v<total;++v)
        vertices[v]={float(v),float(v)+1.f,float(v)+2.f};
    const std::vector<GameSm3ElementRef> declaration{{0u,0u,2u}};
    std::array<GameSm3StreamView,16> streams{};
    streams[0]={reinterpret_cast<const std::uint8_t*>(vertices.data()),stride,total};
    for(std::uint32_t chunk=0;chunk<plan.chunkCount;++chunk) {
        const auto firstRim=1u+chunk*plan.advanceRimVertices;
        const auto count=(std::min)(plan.verticesPerChunk,
                                   1u+total-firstRim);
        assert(count>=3u);
        std::vector<std::uint32_t> indices;
        assert(game_sm3_fan_window_indices(count,100u,indices));
        assert(indices.size()==(count-2u)*3u);
        std::vector<std::uint8_t> raw, expanded;
        assert(game_sm3_copy_native_fan_window(
            streams[0].data,stride,total,firstRim,count,raw));
        assert(game_sm3_assemble_fan_window(
            declaration,streams,firstRim,count,expanded));
        assert(raw.size()==count*stride && expanded.size()==count*16u);
        for(std::uint32_t v=0;v<count;++v) {
            const auto original=v==0u ? 0u : firstRim+v-1u;
            float rawPosition=0.f, unpackedPosition=0.f;
            std::memcpy(&rawPosition,raw.data()+v*stride,sizeof(float));
            std::memcpy(&unpackedPosition,expanded.data()+v*16u,sizeof(float));
            assert(rawPosition==float(original));
            assert(unpackedPosition==float(original));
        }
        for(std::size_t k=0;k<indices.size();k+=3u) {
            auto map=[&](std::uint32_t local) {
                return local==0u ? 0u : firstRim+local-1u; };
            actual.push_back({map(indices[k]),map(indices[k+1u]),
                              map(indices[k+2u])});
        }
    }
    assert(actual.size()==total-2u);
    for(std::uint32_t i=0u;i<total-2u;++i)
        assert((actual[i]==std::array<std::uint32_t,3>{0u,i+1u,i+2u}));
    assert(!game_sm3_plan_native_fan_chunks(total,32u,8u,256u,100u,2u).chunkCount);
    assert(!game_sm3_plan_native_fan_chunks(8u,32u,8u,256u,100u,8u).chunkCount);
    assert(!game_sm3_plan_native_fan_chunks(total,32u,8u,64u,100u,8u).chunkCount);
    std::vector<std::uint32_t> untouched{77u};
    assert(!game_sm3_fan_window_indices(8u,9u,untouched) && untouched==std::vector<std::uint32_t>{77u});
    std::vector<std::uint8_t> keep{55u};
    assert(!game_sm3_copy_native_fan_window(
        streams[0].data,stride,total,16u,4u,keep) && keep==std::vector<std::uint8_t>{55u});
    assert(!game_sm3_assemble_fan_window(
        declaration,streams,16u,4u,keep) && keep==std::vector<std::uint8_t>{55u});
    return 0;
}
