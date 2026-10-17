#include "../../src/vr/d3d11/native_game_stereo_draw_evidence.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::live_game_stereo::may_issue_instanced;
using outrun::vr::dx11::live_game_stereo::color_certifiable;
int main() {
    // Menu/car/race native eye callback: both indexed and non-indexed
    // multi-instance commands preserve ONE genuine source draw ordinal.
    static_assert(may_issue_instanced(3u, 1u, 0u));
    static_assert(may_issue_instanced(6u, 12u, 123u));
    static_assert(may_issue_instanced(4096u, 2u, 5000u));
    // Zero-element/zero-instance calls never fabricate stereo color.
    static_assert(!may_issue_instanced(0u, 2u, 0u));
    static_assert(!may_issue_instanced(3u, 0u, 0u));
    static_assert(!may_issue_instanced(
        3u, 2u, (std::numeric_limits<std::uint64_t>::max)()));
    // Both ordinary and instanced calls must preserve a depth-only draw's
    // command ordinal but reject fabricated color when GPU predication,
    // an absent pixel shader or disabled color output prevents visibility.
    static_assert(color_certifiable(true, true));
    static_assert(!color_certifiable(true, false));
    static_assert(!color_certifiable(false, true));
    assert(color_certifiable(true,true) &&
           !color_certifiable(false,false));
}
