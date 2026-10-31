#include "live_game_sm3_instance_batches.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    using Mode = GameSm3ListSubmissionMode;
    for (auto t : {1u, 2u, 4u}) {
        const std::uint32_t count = t == 1u ? 5u : t == 2u ? 6u : 9u;
        auto compact = game_sm3_list_submission_plan(t, true,
            count, 12u, 3u, 256u);
        assert(compact.mode == Mode::compact_indexed && compact.drawCount == 1u);
        auto segmented = game_sm3_list_submission_plan(t, true,
            count, 12u, 3u, count * 2u);
        assert(segmented.mode == Mode::per_instance && segmented.drawCount == 3u);
        auto linear = game_sm3_list_submission_plan(t, false,
            count, 12u, 3u, count);
        assert(linear.mode == Mode::compact_linear && linear.drawCount == 1u);
        // Original source IB keeps repeated/reordered valid vertices. Each
        // segment uses a distinct native BaseVertexLocation (not a reset IB).
        std::vector<std::uint32_t> original(count);
        for (std::uint32_t i = 0; i < count; ++i) original[i] = (i * 7u) % 12u;
        for (std::uint32_t n = 0; n < segmented.drawCount; ++n)
            for (auto v : original) assert(n * 12u + v < 36u);
        std::vector<std::uint32_t> expanded;
        assert(game_sm3_expand_list_instance_indices(original.data(),
            count, 12u, 3u, expanded));
        for (std::uint32_t n = 0; n < segmented.drawCount; ++n)
            for (std::uint32_t i = 0; i < count; ++i)
                assert(expanded[n * count + i] == n * 12u + original[i]);
        // Reject a malformed source IB before GPU mutation, preserving the
        // legacy D3D9 path rather than incorrectly segmenting invalid data.
        auto old = expanded;
        original[0] = 12u;
        assert(!game_sm3_expand_list_instance_indices(original.data(),
            count, 12u, 3u, expanded));
        assert(expanded == old);
    }
    assert(game_sm3_list_submission_plan(4u, true, 9u, 12u, 3u, 8u).mode == Mode::invalid);
    assert(game_sm3_list_submission_plan(2u, true, 5u, 12u, 3u, 20u).mode == Mode::invalid);
    assert(game_sm3_list_submission_plan(4u, true, 8u, 12u, 3u, 20u).mode == Mode::invalid);
    assert(game_sm3_list_submission_plan(5u, true, 9u, 12u, 3u, 20u).mode == Mode::invalid);
    assert(game_sm3_list_submission_plan(4u, true, 9u, 12u, 1u, 20u).mode == Mode::invalid);
    assert(game_sm3_list_submission_plan(4u, true, 9u, 12u, 3u, 0u).mode == Mode::invalid);
    // A huge source-authored index count must never wrap an allocation.
    assert(game_sm3_list_submission_plan(1u, true,
        (std::numeric_limits<std::uint32_t>::max)(),
        1u, 3u, 1024u).mode == Mode::invalid);
    assert(game_sm3_list_submission_plan(4u, true, 9u,
        (std::numeric_limits<std::uint32_t>::max)(), 3u, 256u).mode == Mode::invalid);
}
