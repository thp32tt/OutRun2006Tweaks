#include "../src/vr/d3d11/native_game_stereo_draw_evidence.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::live_game_stereo::may_issue_instanced;
using outrun::vr::dx11::live_game_stereo::color_certifiable;
using outrun::vr::dx11::live_game_stereo::authored_color_output_ready;
using outrun::vr::dx11::live_game_stereo::full_eye_target_rect;
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
    // Full-size TARGET rectangles take D3D11.0 ClearRenderTargetView on both
    // eyes, so native game scene replay can run without a D3D11.1 context.
    // Cropped menu/HUD rectangles continue to require ClearView and fail
    // closed if the extension is missing; zero-sized targets cannot clear.
    static_assert(full_eye_target_rect(0, 0, 3440, 1440, 3440u, 1440u));
    static_assert(!full_eye_target_rect(0, 0, 3440, 1439, 3440u, 1440u));
    static_assert(!full_eye_target_rect(3, 0, 3440, 1440, 3440u, 1440u));
    static_assert(!full_eye_target_rect(-1, 0, 3440, 1440, 3440u, 1440u));
    static_assert(!full_eye_target_rect(0, 0, 3440, 1440, 0u, 1440u));
    // Original D3D9 TARGET Clear is authentic eye color, not fabricated
    // geometry. Admit depth-only draws following a full seed, while rejecting
    // a terminal Clear that erased the last native game geometry.
    static_assert(authored_color_output_ready(5u, 0u, 0u, 1u, 0u));
    static_assert(authored_color_output_ready(5u, 0u, 0u, 2u, 4u));
    static_assert(!authored_color_output_ready(5u, 0u, 0u, 2u, 5u));
    static_assert(!authored_color_output_ready(0u, 0u, 0u, 1u, 0u));
    static_assert(authored_color_output_ready(5u, 0u, 1u, 2u, 5u));
    assert(color_certifiable(true,true) &&
           !color_certifiable(false,false) &&
           authored_color_output_ready(5u, 0u, 0u, 1u, 0u) &&
           !authored_color_output_ready(5u, 0u, 0u, 1u, 5u));
}
