#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>

using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
constexpr bool failed_source_draw_regression() {
    GameNativeFrameBatch menu{};
    if (!menu.accepts_full(0u)) return false;
    menu.succeeded(false);
    menu.record_source_draw(0u);
    if (!menu.publishable_full(true, 1u)) return false;
    // Original D3D9 Draw #1 then fails after speculative native capture.
    menu.succeeded(false);
    menu.record_source_draw(1u);
    menu.abort();
    if (menu.publishable_full(true, 2u) || menu.accepts_full(2u)) return false;
    // First game Draw failure must also forbid a later native Draw splice.
    GameNativeFrameBatch vehicle{};
    vehicle.abort();
    if (vehicle.accepts_full(0u) || vehicle.publishable_full(true, 0u)) return false;
    // A later proven whole-backbuffer Clear may start a new continuous scene.
    menu.reset();
    if (!menu.accepts_full(0u)) return false;
    menu.succeeded(false);
    menu.record_source_draw(0u);
    if (!menu.publishable_full(true, 1u)) return false;
    // Even a failed trailing original Draw after a valid batch is not invisible.
    menu.abort();
    return !menu.publishable_full(true, 1u);
}
static_assert(failed_source_draw_regression(), "native game frame must respect original Draw HRESULT");
int main() { assert(failed_source_draw_regression()); }
