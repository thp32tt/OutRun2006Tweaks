#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
// Each game source instance has 2 vertices * 2 FLOAT4 declaration elements.
constexpr auto chunks = game_sm3_plan_native_instance_chunk(2u, 5u, 32u, 100u, 160u);
static_assert(chunks.instancesPerChunk == 2u && chunks.firstUploadBytes == 128u);
static_assert(game_sm3_plan_native_instance_chunk(
    2u, 5u, 32u, 100u, 64u).instancesPerChunk == 1u);
static_assert(game_sm3_plan_native_instance_chunk(
    2u, 5u, 32u, 3u, 160u).instancesPerChunk == 1u);
static_assert(game_sm3_plan_native_instance_chunk(
    2u, 5u, 32u, 100u, 63u).instancesPerChunk == 0u);
static_assert(game_sm3_plan_native_instance_chunk(
    2u, 5u, UINT32_MAX, 100u, 160u).instancesPerChunk == 0u);
static_assert(game_sm3_plan_native_instance_chunk(
    0u, 5u, 32u, 100u, 160u).instancesPerChunk == 0u);
int main() {
    const float vertices[] = {11.f,22.f};
    const float records[] = {101.f,202.f,303.f};
    std::array<GameSm3StreamView,16> streams{};
    streams[0] = {reinterpret_cast<const std::uint8_t*>(vertices),4u,2u};
    streams[1] = {reinterpret_cast<const std::uint8_t*>(records),4u,3u};
    const std::vector<GameSm3ElementRef> decl{{0u,0u,0u},{1u,0u,0u}};
    std::array<std::uint32_t,16> step{};
    step[1] = 2u;
    std::vector<std::uint8_t> full;
    assert(game_sm3_assemble_instanced_streams(decl,streams,2u,5u,step,full));
    // Two original instances in each full GPU upload; final chunk is short.
    std::vector<std::uint8_t> chunk;
    std::uint32_t draws = 0u, uploads = 0u;
    for (std::uint32_t first = 0u; first < 5u;
         first += chunks.instancesPerChunk) {
        const std::uint32_t count = (std::min)(
            chunks.instancesPerChunk, 5u-first);
        assert(game_sm3_assemble_instanced_streams(
            decl,streams,2u,count,step,chunk,first));
        assert(chunk.size() == std::size_t(count)*64u);
        assert(std::memcmp(chunk.data(),full.data()+first*64u,
                           chunk.size()) == 0);
        ++uploads;
        for (std::uint32_t local=0u;local<count;++local) {
            const std::uint32_t base=local*2u; // D3D11 Draw/DrawIndexed
            float vertex{},record{};
            std::memcpy(&vertex,chunk.data()+base*32u,4u);
            std::memcpy(&record,chunk.data()+base*32u+16u,4u);
            assert(vertex==11.f && record==records[(first+local)/2u]);
            ++draws;
        }
    }
    assert(uploads == 3u && draws == 5u);
    const auto preserved=chunk;
    streams[1].vertexCount=2u; // final source INSTANCEDATA record missing
    assert(!game_sm3_assemble_instanced_streams(
        decl,streams,2u,1u,step,chunk,4u));
    assert(chunk==preserved);
}
