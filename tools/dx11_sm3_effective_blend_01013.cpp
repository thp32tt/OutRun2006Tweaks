// Actual shader-bound game Draw needs effective RGB, not ignored D3D9 destination factor.
#include "../src/vr/d3d11/live_game_sm3_composite.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    assert(live_sm3_effective_dest_factor(12u, 14u) == 6u);
    assert(live_sm3_effective_dest_factor(13u, 15u) == 5u);
    assert(!live_sm3_needs_dynamic_blend_factor(true, 12u, 14u, false, 0u, 0u));
    assert(!live_sm3_needs_dynamic_blend_factor(true, 13u, 15u, false, 0u, 0u));
    assert(live_sm3_needs_dynamic_blend_factor(true, 2u, 14u, false, 0u, 0u));
    assert(live_sm3_needs_dynamic_blend_factor(true, 12u, 14u, true, 14u, 2u));
    assert(live_sm3_needs_dynamic_blend_factor(true, 13u, 15u, true, 2u, 15u));
    assert(!live_sm3_needs_dynamic_blend_factor(false, 14u, 15u, true, 14u, 15u));
    // Production Draw uses COLORWRITEENABLE, so ignored alpha/RGB state
    // must not require a transient per-Draw GPU OM constant. With alpha
    // enabled and no independent alpha, RGB factors still govern alpha.
    assert(!live_sm3_needs_dynamic_blend_factor(
        true, 2u, 2u, true, 14u, 15u, 0x07u));
    assert(live_sm3_needs_dynamic_blend_factor(
        true, 2u, 2u, true, 14u, 15u, 0x08u));
    assert(!live_sm3_needs_dynamic_blend_factor(
        true, 14u, 2u, true, 2u, 2u, 0x08u));
    assert(live_sm3_needs_dynamic_blend_factor(
        true, 14u, 2u, false, 2u, 2u, 0x08u));
    assert(!live_sm3_needs_dynamic_blend_factor(
        true, 14u, 15u, true, 14u, 15u, 0x00u));
    assert(!live_sm3_needs_dynamic_blend_factor(
        true, 14u, 15u, true, 14u, 15u, 0x10u));
}
