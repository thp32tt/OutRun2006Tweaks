#include "live_game_sm3_connected_submission.hpp"
#include "live_game_sm3_connected_instances.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    using Mode = GameSm3ConnectedSubmissionMode;
    for (std::uint32_t type : {3u, 5u, 6u}) {
        const auto small = game_sm3_connected_submission_plan(type, 5u, 5u, 3u, 128u);
        assert(small.mode == Mode::compact_indexed && small.drawCount == 1u);
        std::vector<std::uint32_t> expanded;
        assert(game_sm3_expand_connected_instance_indices(
            type, nullptr, 5u, 5u, 3u, 128u, expanded));
        const auto large = game_sm3_connected_submission_plan(type, 5u, 5u, 3u, 10u);
        assert(large.mode == Mode::per_instance && large.drawCount == 3u);
        // Each segmented source instance uses the original span and an
        // independent base vertex: even strips never bridge two instances.
        const std::uint32_t source[] = {4u, 3u, 2u, 1u, 0u};
        for (std::uint32_t n = 0u; n < large.drawCount; ++n) {
            assert(n * 5u + source[0] < 15u);
            assert(n * 5u + source[4] < 15u);
        }
    }
    // Indexed sourceCount may exceed verticesPerInstance (reused indices).
    assert(game_sm3_connected_submission_plan(5u, 5u, 4u, 3u, 128u).mode ==
           Mode::compact_indexed);
    for (const auto type : {0u, 1u, 2u, 4u, 7u})
        assert(game_sm3_connected_submission_plan(type, 5u, 5u, 3u, 10u).mode ==
               Mode::invalid);
    assert(game_sm3_connected_submission_plan(5u, 1u, 5u, 3u, 10u).mode ==
           Mode::invalid);
    assert(game_sm3_connected_submission_plan(5u, 5u, 5u, 1u, 10u).mode ==
           Mode::invalid);
    assert(game_sm3_connected_submission_plan(5u, 5u, 5u, 3u, 0u).mode ==
           Mode::invalid);
    // No multiplication overflow may falsely authorize an expanded GPU IB.
    const auto overflow = game_sm3_connected_submission_plan(
        5u, (std::numeric_limits<std::uint32_t>::max)(),
        (std::numeric_limits<std::uint32_t>::max)(),
        (std::numeric_limits<std::uint32_t>::max)(),
        (std::numeric_limits<std::uint32_t>::max)());
    assert(overflow.mode == Mode::per_instance);
}
