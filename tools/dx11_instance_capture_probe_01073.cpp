#include "../src/vr/d3d11/native_game_instance_stream_capture.hpp"
#include <cassert>
#include <array>
#include <cstdint>
using outrun::vr::dx11::live_game_frame::game_native_instance_stream_capture;
int main() {
    constexpr std::uint32_t indexed = 0x40000000u;
    constexpr std::uint32_t instanced = 0x80000000u;
    constexpr auto vertexRate = game_native_instance_stream_capture(indexed | 5u, 1u, 3u);
    static_assert(vertexRate.valid && !vertexRate.instanceRate && vertexRate.sourceSlots == 3u);
    constexpr auto rate1 = game_native_instance_stream_capture(indexed | 5u, instanced | 1u, 3u);
    static_assert(rate1.valid && rate1.instanceRate && rate1.sourceSlots == 5u);
    constexpr auto rate2 = game_native_instance_stream_capture(indexed | 5u, instanced | 2u, 3u);
    static_assert(rate2.valid && rate2.instanceRate && rate2.sourceSlots == 3u);
    constexpr auto rate9 = game_native_instance_stream_capture(indexed | 5u, instanced | 9u, 3u);
    static_assert(rate9.valid && rate9.instanceRate && rate9.sourceSlots == 1u);
    static_assert(game_native_instance_stream_capture(1u, 1u, 3u).valid);
    static_assert(!game_native_instance_stream_capture(1u, instanced | 1u, 3u).valid);
    static_assert(!game_native_instance_stream_capture(indexed, instanced | 1u, 3u).valid);
    static_assert(!game_native_instance_stream_capture(indexed | 5u, instanced, 3u).valid);
    static_assert(!game_native_instance_stream_capture(0u, 1u, 3u).valid);
    static_assert(!game_native_instance_stream_capture(indexed | 5u, 1u, 0u).valid);
    static_assert(!game_native_instance_stream_capture(indexed | 5u, 0xC0000001u, 3u).valid);
    // Five instances, step two: shader records 0,0,1,1,2, not vertices 100,102,104.
    constexpr std::array<int, 3> positions{10, 20, 30};
    constexpr std::array<int, 5> expected{10, 10, 20, 20, 30};
    for (std::uint32_t i = 0u; i < 5u; ++i)
        assert(positions[i / 2u] == expected[i]);
    return 0;
}
