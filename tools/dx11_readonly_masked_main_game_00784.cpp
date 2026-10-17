#include "../src/vr/d3d11/native_game_masked_draw.hpp"
#include "../src/vr/d3d11/native_game_offscreen_pass.hpp"
#include "../src/vr/d3d11/native_game_fragment_reject.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;

// Menu Draw -> read-only stencil and color-disabled bound MRT DrawIndexed ->
// X8 alpha-only no-write Draw -> actual race DrawIndexed -> same Present.
constexpr bool native_frame_with_readonly_main_draws() {
    GameNativeFrameBatch game{};
    if (!game.accepts_full_on_source_target(0u, true)) return false;
    game.succeeded(true); game.record_source_draw(0u);
    const bool noMainStencilWrite = GameNativeOffscreenPass::no_main_stencil_write(true, true, 0u);
    const bool noExtraMrtWrite = GameNativeOffscreenPass::inactive_extra_mrt(true, 0u);
    if (!noMainStencilWrite || !noExtraMrtWrite ||
        !GameNativeMaskedDraw::no_visible_target_write_source_draw(
            true, true, 0u, true, true, false, !noMainStencilWrite, !noExtraMrtWrite))
        return false;
    if (!game.absorb_empty_source_draw(1u)) return false;
    if (!GameNativeMaskedDraw::no_visible_target_write_source_draw(
            true, true, 0x08u, false, true, false, !noMainStencilWrite, !noExtraMrtWrite))
        return false;
    if (!game.absorb_empty_source_draw(2u)) return false;
    if (!game.accepts_full_on_source_target(3u, true)) return false;
    game.succeeded(true); game.record_source_draw(3u);
    return game.submitted == 2u && game.publishable_full(true, 4u);
}
constexpr bool unsafe_state_keeps_original_d3d9_fallback() {
    using M = GameNativeMaskedDraw;
    using O = GameNativeOffscreenPass;
    using F = GameNativeFragmentReject;
    // A writable or UNKNOWN stencil mask, writable/unknown MRT and real A8
    // destination-alpha or main Z writes must not be silently dropped.
    if (O::no_main_stencil_write(true, false, 0u) ||
        O::no_main_stencil_write(true, true, 1u) ||
        O::inactive_extra_mrt(false, 0u) ||
        O::inactive_extra_mrt(true, 0x08u) ||
        M::no_visible_target_write_source_draw(true, true, 0x08u, true,
                                               true, false, false, false) ||
        M::no_visible_target_write_source_draw(true, true, 0u, false,
                                               true, true, false, false) ||
        M::no_visible_target_write_source_draw(true, false, 0u, false,
                                               true, false, false, false))
        return false;
    if (F::no_target_write(true, true, true, true,
                           false, true, F::kNever, false, 0u))
        return false; // stencil writer can mutate Z/S despite alpha NEVER
    GameNativeFrameBatch game{};
    game.succeeded(true); game.record_source_draw(0u);
    game.abort(); // unknown/writable RT1 or stencil must abort, not publish
    return !game.absorb_empty_source_draw(1u) &&
           !game.publishable_full(true, 2u);
}
static_assert(native_frame_with_readonly_main_draws());
static_assert(unsafe_state_keeps_original_d3d9_fallback());
int main() {
    assert(native_frame_with_readonly_main_draws());
    assert(unsafe_state_keeps_original_d3d9_fallback());
}
