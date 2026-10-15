#include "../src/vr/d3d11/native_game_offscreen_pass.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool hardware_mrt_slot_boundaries() {
    if (GameNativeOffscreenPass::valid_mrt_count(0u) ||
        GameNativeOffscreenPass::valid_mrt_count(5u)) return false;
    for (std::uint32_t count = 1u; count <= 4u; ++count) {
        if (!GameNativeOffscreenPass::valid_mrt_count(count)) return false;
        // Slot zero is the active RT; all actual extra slots fit [1,count).
        std::uint32_t queried = 0u;
        for (std::uint32_t i = 1u; i < count; ++i) ++queried;
        if (queried != count - 1u) return false;
    }
    return true;
}
constexpr bool game_offscreen_interleave() {
    GameNativeFrameBatch batch{};
    if (!batch.accepts_full_on_source_target(0u, true)) return false;
    batch.succeeded(true); batch.record_source_draw(0u);
    if (!GameNativeOffscreenPass::preserve_transition(
            true, true, true, false, true)) return false;
    if (!GameNativeOffscreenPass::source_has_no_main_writes(
            true, true, true, true, true, true, false)) return false;
    if (!batch.absorb_empty_source_draw(1u)) return false;
    if (!batch.accepts_full_on_source_target(2u, true)) return false;
    batch.succeeded(false); batch.record_source_draw(2u);
    return batch.submitted == 2u && batch.publishable_full(true, 3u);
}
constexpr bool leading_offscreen_then_game() {
    GameNativeFrameBatch batch{};
    if (!batch.absorb_empty_source_draw(0u, true)) return false;
    if (!batch.accepts_full_on_source_target(1u, true)) return false;
    batch.succeeded(false); batch.record_source_draw(1u);
    return batch.submitted == 1u && batch.publishable_full(true, 2u);
}
constexpr bool unsupported_writes_fallback() {
    const auto safe=[](bool target, bool depth, bool stencil, bool mrt) {
        return GameNativeOffscreenPass::source_has_no_main_writes(
            true, true, target, depth, stencil, mrt, false);
    };
    GameNativeFrameBatch batch{};
    batch.succeeded(false); batch.record_source_draw(0u);
    if (safe(false, true, true, true) || safe(true, false, true, true) ||
        safe(true, true, false, true) || safe(true, true, true, false) ||
        GameNativeOffscreenPass::source_has_no_main_writes(
            true, false, true, true, true, true, false) ||
        GameNativeOffscreenPass::preserve_transition(
            true, true, false, false, true) ||
        GameNativeOffscreenPass::preserve_transition(
            true, true, true, true, true)) return false;
    batch.abort();
    return !batch.absorb_empty_source_draw(1u) &&
        !batch.publishable_full(true, 2u);
}
static_assert(hardware_mrt_slot_boundaries());
static_assert(game_offscreen_interleave());
static_assert(leading_offscreen_then_game());
static_assert(unsupported_writes_fallback());
int main() {
    assert(hardware_mrt_slot_boundaries());
    assert(game_offscreen_interleave());
    assert(leading_offscreen_then_game());
    assert(unsupported_writes_fallback());
}
