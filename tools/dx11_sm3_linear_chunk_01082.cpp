// Real game D3D9 SM3 multi-stream packed list -> native D3D11 bounded
// Draw chunks without cutting a POINT/LINELIST/TRIANGLELIST primitive.
#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    for (std::uint32_t type : {1u, 2u, 4u}) {
        const std::uint32_t group = type == 1u ? 1u : type == 2u ? 2u : 3u;
        const auto plan = game_sm3_plan_native_linear_chunks(
            type, false, group * 11u, 32u, group * 12u,
            group * 3u * 32u + 1u, 6u);
        assert(plan.verticesPerChunk == group * 3u);
        assert(plan.chunkCount == 4u);
        std::uint32_t consumed = 0u;
        for (std::uint32_t chunk = 0u; chunk < plan.chunkCount; ++chunk) {
            const std::uint32_t count = consumed + plan.verticesPerChunk >
                group * 11u ? group * 11u - consumed : plan.verticesPerChunk;
            assert(consumed % group == 0u && count % group == 0u);
            consumed += count;
        }
        assert(consumed == group * 11u);
        assert(!game_sm3_plan_native_linear_chunks(
            type, true, group * 11u, 32u, 999u, 100u, 100u).chunkCount);
    }
    // Connected strips/fans and malformed primitive endings stay D3D9.
    for (std::uint32_t type : {3u, 5u, 6u, 7u}) {
        assert(!game_sm3_plan_native_linear_chunks(
            type, false, 33u, 32u, 32u, 128u, 20u).chunkCount);
    }
    assert(!game_sm3_plan_native_linear_chunks(
        4u, false, 32u, 32u, 32u, 128u, 20u).chunkCount);
    assert(!game_sm3_plan_native_linear_chunks(
        4u, false, 33u, 32u, 32u, 64u, 3u).chunkCount);
    // Repack two authentic source streams with independent strides and
    // verify absolute vertex addressing across successive GPU slices.
    std::array<std::uint8_t, 12u * 12u> positions{};
    std::array<std::uint8_t, 8u * 12u> uvs{};
    for (std::uint32_t v = 0u; v < 12u; ++v) {
        const float p[3] = {float(v), float(v) + 0.5f, float(v) + 1.f};
        const float uv[2] = {float(v) / 16.f, float(v) / 8.f};
        std::memcpy(positions.data() + v * 12u, p, sizeof(p));
        std::memcpy(uvs.data() + v * 8u, uv, sizeof(uv));
    }
    const std::vector<GameSm3ElementRef> elements{{0u,0u,2u},{1u,0u,1u}};
    std::array<GameSm3StreamView,16> streams{};
    streams[0] = {positions.data(),12u,12u};
    streams[1] = {uvs.data(),8u,12u};
    std::vector<std::uint8_t> combined, first, second;
    assert(game_sm3_assemble_streams(elements, streams, 12u, combined));
    assert(game_sm3_assemble_streams(elements, streams, 6u, first, 0u));
    assert(game_sm3_assemble_streams(elements, streams, 6u, second, 6u));
    assert(combined.size() == 12u * 32u && first.size() == 6u * 32u);
    assert(std::memcmp(combined.data(), first.data(), first.size()) == 0);
    assert(std::memcmp(combined.data() + first.size(),
                       second.data(), second.size()) == 0);
    const auto original = second;
    assert(!game_sm3_assemble_streams(elements, streams, 7u, second, 6u));
    assert(second == original); // failed chunk cannot overwrite earlier data
    assert(!game_sm3_assemble_streams(elements, streams, 1u, second, 13u));
    assert(second == original);
}
