#include "../src/vr/d3d11/native_game_masked_draw.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;

static_assert(GameNativeMaskedDraw::accepts_source_mask(0x07u, false, false, false));
static_assert(!GameNativeMaskedDraw::accepts_source_mask(0x08u, false, true, false));
static_assert(!GameNativeMaskedDraw::accepts_source_mask(0u, false, true, true));
static_assert(GameNativeMaskedDraw::accepts_source_mask(0x08u, true, true, false));
static_assert(GameNativeMaskedDraw::accepts_source_mask(0u, true, false, true));
static_assert(GameNativeMaskedDraw::accepts_source_mask(0x08u, true, false, true));
static_assert(!GameNativeMaskedDraw::accepts_source_mask(0x08u, true, false, false));
static_assert(!GameNativeMaskedDraw::accepts_source_mask(0u, true, true, false));
static_assert(!GameNativeMaskedDraw::accepts_source_mask(0x10u, true, true, true));
static_assert(GameNativeMaskedDraw::effective_native_mask(0x08u, true) == 0x08u);
static_assert(GameNativeMaskedDraw::effective_native_mask(0x08u, false) == 0u);
static_assert(GameNativeMaskedDraw::effective_native_mask(0x0fu, false) == 0x07u);
// Source Clear -> game-authored alpha-only Draw -> depth-writing DrawIndexed
// must be accepted in the full-size continuous batch and reach Present.
// The original D3D9 game Draw/Present/input always execute independently.
constexpr bool source_batch_with_masked_draws() {
    GameNativeFrameBatch batch{};
    if (!batch.accepts_full_on_source_target(0u, true)) return false;
    batch.succeeded(false); batch.record_source_draw(0u);
    if (!batch.accepts_full_on_source_target(1u, true)) return false;
    batch.succeeded(true); batch.record_source_draw(1u);
    return batch.publishable_full(true, 2u);
}
static_assert(source_batch_with_masked_draws());
int main() {
    assert(source_batch_with_masked_draws());
    assert(!GameNativeMaskedDraw::accepts_source_mask(0u, true, false, false));
}
