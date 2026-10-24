#include "../src/vr/d3d11/native_game_inert_stencil_mrt.hpp"
#include "../src/vr/d3d11/native_game_offscreen_pass.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
using A = GameNativeInertStencilMrt;
constexpr bool menu_car_race_real_gpu_draw_continues() {
    GameNativeFrameBatch batch{};
    GameNativeClearColor clear{};
    clear.record(0x111u, 0x222u, 0xff102030u, true, false, 0x333u);
    if (!A::stencil_equivalent_to_disabled(true, true, A::kCompareAlways, 0u, false) ||
        !A::extra_target_inert(true, 0u) ||
        !clear.main_depth_still_bound(0x333u)) return false;
    if (!batch.accepts_full_on_source_target(0u, clear.matches(0x111u, 0x222u)))
        return false;
    batch.succeeded(true); batch.record_source_draw(0u);
    if (!batch.accepts_full_on_source_target(1u, true) ||
        !batch.accepts_source_draw(1u, true)) return false;
    batch.succeeded(true); batch.record_source_draw(1u);
    if (!batch.accepts_full_on_source_target(2u, true) ||
        !batch.accepts_source_draw(2u, true)) return false;
    batch.succeeded(true); batch.record_source_draw(2u);
    return batch.submitted == 3u && batch.publishable_full(true, 3u);
}
constexpr bool unsafe_writable_or_conditional_state_falls_back() {
    if (A::stencil_equivalent_to_disabled(true, false, 8u, 0u, false) ||
        A::stencil_equivalent_to_disabled(true, true, 7u, 0u, false) ||
        A::stencil_equivalent_to_disabled(true, true, 8u, 1u, false) ||
        A::stencil_equivalent_to_disabled(true, true, 8u, 0u, true) ||
        A::extra_target_inert(false, 0u) ||
        A::extra_target_inert(true, 0x8u) ||
        A::extra_target_inert(true, 0x100u)) return false;
    GameNativeClearColor clear{};
    clear.record(1u, 2u, 0u, true, false, 3u);
    if (clear.main_depth_still_bound(4u) || clear.main_depth_still_bound(0u))
        return false;
    GameNativeFrameBatch batch{};
    batch.succeeded(true); batch.record_source_draw(0u);
    batch.abort();
    return !batch.publishable_full(true, 1u) && !batch.accepts_full(1u);
}
static_assert(menu_car_race_real_gpu_draw_continues());
static_assert(unsafe_writable_or_conditional_state_falls_back());
int main() {
    assert(menu_car_race_real_gpu_draw_continues());
    assert(unsafe_writable_or_conditional_state_falls_back());
}
