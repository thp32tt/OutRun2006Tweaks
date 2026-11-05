#include "../src/vr/d3d11/native_game_masked_draw.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;

constexpr bool x8_no_write(std::uint32_t mask, bool alphaPlane,
                           bool depthWrite, bool stencil, bool mrt) {
    return GameNativeMaskedDraw::no_visible_target_write_source_draw(
        true, true, mask, alphaPlane, true, depthWrite, stencil, mrt);
}
static_assert(x8_no_write(0x08u, false, false, false, false));
static_assert(x8_no_write(0x00u, true, false, false, false));
static_assert(!x8_no_write(0x08u, true, false, false, false)); // A8 dest alpha
static_assert(!x8_no_write(0x08u, false, true, false, false)); // Z write
static_assert(!x8_no_write(0x08u, false, false, true, false)); // stencil
static_assert(!x8_no_write(0x08u, false, false, false, true)); // MRT
static_assert(!x8_no_write(0x09u, false, false, false, false)); // RGB
static_assert(!x8_no_write(0x18u, false, false, false, false)); // illegal mask
static_assert(!GameNativeMaskedDraw::no_visible_target_write_source_draw(
    true, false, 0x08u, false, true, false, false, false)); // unseeded
static_assert(!GameNativeMaskedDraw::no_visible_target_write_source_draw(
    false, true, 0x08u, false, true, false, false, false)); // inset

// Full game backbuffer Clear -> Draw -> X8 alpha-only menu DrawIndexed ->
// race DrawIndexed -> same-Present publication. Source ordinal 1 is real,
// but its X8 alpha write contributes no native pixels. Native RTV is retained.
constexpr bool menu_vehicle_race_continuity() {
    GameNativeFrameBatch frame{};
    if (!frame.accepts_full_on_source_target(0u, true)) return false;
    frame.succeeded(false); frame.record_source_draw(0u);
    if (!x8_no_write(0x08u, false, false, false, false) ||
        !frame.absorb_empty_source_draw(1u, true)) return false;
    if (frame.submitted != 1u || frame.postDrawEmptySourceDraws != 1u ||
        !frame.accepts_full_on_source_target(2u, true)) return false;
    frame.succeeded(true); frame.record_source_draw(2u);
    return frame.publishable_full(true, 3u) && frame.submitted == 2u;
}
constexpr bool fallback_on_real_alpha_write() {
    GameNativeFrameBatch frame{};
    frame.succeeded(false); frame.record_source_draw(0u);
    if (x8_no_write(0x08u, true, false, false, false)) return false;
    frame.abort(); // Existing D3D9 game Draw/Present/input remain authoritative.
    return !frame.publishable_full(true, 2u);
}
static_assert(menu_vehicle_race_continuity());
static_assert(fallback_on_real_alpha_write());
int main() {
    assert(menu_vehicle_race_continuity());
    assert(fallback_on_real_alpha_write());
}
