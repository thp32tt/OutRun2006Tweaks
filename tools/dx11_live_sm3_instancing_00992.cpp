#include "../src/vr/d3d11/live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
static float component(const std::vector<std::uint8_t>& b,
                       std::size_t vertex, std::size_t attribute) {
    float f = 0.f;
    std::memcpy(&f, b.data() + vertex * 32u + attribute * 16u, sizeof(f));
    return f;
}
int main() {
    const float positions[3]{1.f, 2.f, 3.f};
    const float instances[2]{10.f, 20.f};
    const std::array<GameSm3StreamView,4> streams{{
        {reinterpret_cast<const std::uint8_t*>(positions),4u,3u},
        {reinterpret_cast<const std::uint8_t*>(instances),4u,2u},
        {}, {}
    }};
    const std::vector<GameSm3ElementRef> elements{{0u,0u,0u},{1u,0u,0u}};
    std::vector<std::uint8_t> packed;
    const std::array<std::uint32_t,4> frequency{{0u,2u,0u,0u}};
    assert(game_sm3_assemble_instanced_streams(
        elements, streams, 3u, 3u, frequency, packed));
    assert(packed.size() == 9u * 32u);
    assert(component(packed,0u,0u)==1.f && component(packed,2u,0u)==3.f);
    assert(component(packed,3u,0u)==1.f && component(packed,8u,0u)==3.f);
    assert(component(packed,0u,1u)==10.f && component(packed,5u,1u)==10.f);
    assert(component(packed,6u,1u)==20.f && component(packed,8u,1u)==20.f);
    const auto copy = packed;
    // Missing instance records, zero source count, invalid step/stream and
    // 32MiB expansion overflow must not corrupt an earlier GPU upload.
    auto shortStreams = streams;
    shortStreams[1].vertexCount = 1u;
    assert(!game_sm3_assemble_instanced_streams(
        elements, shortStreams, 3u, 3u, frequency, packed));
    assert(!game_sm3_assemble_instanced_streams(
        elements, streams, 3u, 0u, frequency, packed));
    assert(!game_sm3_assemble_instanced_streams(
        elements, streams, 1000000u, 1000000u, frequency, packed));
    const std::array<std::uint32_t,4> illegal{{1u,2u,0u,0u}};
    assert(!game_sm3_assemble_instanced_streams(
        elements, streams, 3u, 3u, illegal, packed));
    assert(packed == copy);
    // Existing vertex-only menu/race path remains source-order preserving.
    std::vector<std::uint8_t> regular;
    assert(game_sm3_assemble_streams(
        {{0u,0u,0u}}, streams, 3u, regular));
    assert(regular.size() == 3u * 16u);
    return 0;
}
