// Real SM3 D3D9 instanced LINESTRIP, TRIANGLESTRIP, TRIANGLEFAN:
// one D3D11 DrawIndexed per bounded GPU vertex chunk, no cross-instance edges.
#include "live_game_sm3_connected_submission.hpp"
#include "live_game_sm3_connected_instances.hpp"
#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <limits>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    // Eight game instances, GPU space for three per native upload => 3 GPU
    // submissions (3+3+2), instead of 8 separate game-geometry Draws.
    constexpr auto chunk = game_sm3_plan_native_instance_chunk(
        5u, 8u, 16u, 15u, 240u);
    static_assert(chunk.instancesPerChunk == 3u);
    for (std::uint32_t type : {3u, 5u, 6u}) {
        const auto plan = game_sm3_segmented_connected_submission_plan(
            type, false, false, 5u, 5u, 8u, chunk.instancesPerChunk, 128u);
        assert(plan.grouped && plan.batches == 3u);
        const std::array<std::uint32_t, 5> local{{4u,3u,2u,1u,0u}};
        std::vector<std::uint32_t> expanded;
        for (const std::uint32_t count : {3u,2u,1u}) {
            assert(game_sm3_expand_connected_instance_indices(
                type, local.data(), 5u, 5u, count, 128u, expanded));
            const std::size_t perInstance =
                (5u - (type == 3u ? 1u : 2u)) * (type == 3u ? 2u : 3u);
            assert(expanded.size() == perInstance * count);
            // Every generated vertex remains in the proper local chunk
            // instance range; no last-to-first strip/fan connection.
            for (std::size_t n = 0; n < count; ++n)
                for (std::size_t j = 0; j < perInstance; ++j) {
                    const auto index = expanded[n * perInstance + j];
                    assert(index >= n * 5u && index < (n + 1u) * 5u);
                }
            if (type == 5u) {
                // Alternating source strip winding is preserved with reversed
                // source indices, not merely ordered D3D11 triangle fans.
                assert(expanded[0] == 4u && expanded[1] == 3u);
                assert(expanded[3] == 2u && expanded[4] == 3u);
            }
            if (type == 6u) {
                assert(expanded[0] == 4u && expanded[1] == 3u &&
                       expanded[2] == 2u);
            }
        }
        // Unindexed game stream and a one-instance final chunk.
        assert(game_sm3_expand_connected_instance_indices(
            type, nullptr, 5u, 5u, 1u, 128u, expanded));
        assert(expanded.front() == 0u);
        const auto snapshot = expanded;
        const std::array<std::uint32_t,5> bad{{0u,1u,2u,3u,5u}};
        assert(!game_sm3_expand_connected_instance_indices(
            type, bad.data(), 5u, 5u, 2u, 128u, expanded));
        assert(expanded == snapshot);
    }
    // An authentic strip/fan triangle expansion now supports both POINT
    // occurrence and wireframe batching without cross-instance seams.
    for (const auto type : {5u, 6u}) {
        assert(game_sm3_segmented_connected_submission_plan(
            type, true, false, 5u, 5u, 8u, 3u, 128u).grouped);
        assert(game_sm3_segmented_connected_submission_plan(
            type, false, true, 5u, 5u, 8u, 3u, 128u).grouped);
    }
    // Unsupported line polygon fill, independent list, one chunk,
    // inadequate IB capacity, and arithmetic overflow still fail closed.
    assert(!game_sm3_segmented_connected_submission_plan(
        3u, true, false, 5u, 5u, 8u, 3u, 128u).grouped);
    assert(!game_sm3_segmented_connected_submission_plan(
        3u, false, true, 5u, 5u, 8u, 3u, 128u).grouped);
    assert(!game_sm3_segmented_connected_submission_plan(
        4u, false, false, 5u, 5u, 8u, 3u, 128u).grouped);
    assert(!game_sm3_segmented_connected_submission_plan(
        5u, false, false, 5u, 5u, 3u, 3u, 128u).grouped);
    assert(!game_sm3_segmented_connected_submission_plan(
        5u, false, false, 5u, 5u, 8u, 3u, 20u).grouped);
    assert(!game_sm3_segmented_connected_submission_plan(
        5u, false, false, 0xffffffffu, 0xffffffffu, 8u, 3u,
        0xffffffffu).grouped);
}
