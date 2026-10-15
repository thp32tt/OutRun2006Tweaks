#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cstdint>
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;

constexpr bool full_game_empty_draw_contract() noexcept {
    GameNativeFrameBatch game{};
    // No prior native pixels/clear: an empty call cannot invent a frame.
    if (game.absorb_empty_source_draw(0u) || game.publishable_full(true, 1u))
        return false;
    if (!game.accepts_full_seeded(0u, true)) return false;
    game.succeeded(true);
    game.record_source_draw(0u);
    game.depthDirection = 2u;
    // The real Draw precedes one or more successful empty Draws.
    if (!game.absorb_empty_source_draw(1u) ||
        !game.absorb_empty_source_draw(2u) ||
        game.submitted != 1u || game.postDrawEmptySourceDraws != 2u ||
        game.depthDirection != 2u ||
        !game.accepts_full_seeded(3u, false)) return false;
    game.succeeded(true, true);
    game.record_source_draw(3u);
    // Exact whole game source stream is still publishable at this Present.
    if (!game.publishable_full(true, 4u) ||
        game.publishable_full(true, 3u) ||
        game.publishable_full(false, 4u)) return false;
    // Skipped/duplicated game ordinals and an aborted scene never re-enter.
    if (game.absorb_empty_source_draw(6u) ||
        game.absorb_empty_source_draw(3u)) return false;
    game.abort();
    if (game.absorb_empty_source_draw(4u) ||
        game.publishable_full(true, 4u)) return false;
    // Recovery requires a new full-color Clear and first real draw.
    game.reset();
    if (game.absorb_empty_source_draw(0u) || !game.accepts_full_seeded(0u,true))
        return false;
    game.succeeded(false);
    game.record_source_draw(0u);
    if (!game.absorb_empty_source_draw(1u) ||
        !game.publishable_full(true, 2u)) return false;
    return true;
}
static_assert(full_game_empty_draw_contract(),
              "Live full-frame successful empty Draws must keep contiguous game-source order");
// Real menu/car/race streams may contain successful empty calls after the
// full TARGET Clear but BEFORE the first nonempty Draw. They advance source
// order without generating pixels or suppressing the first native RTV clear.
constexpr bool leading_game_empty_draw_contract() noexcept {
    GameNativeFrameBatch game{};
    if (game.absorb_empty_source_draw(0u) ||
        !game.absorb_empty_source_draw(0u, true) ||
        !game.absorb_empty_source_draw(1u, true) ||
        !game.first_draw() || game.publishable_full(true, 2u) ||
        !game.can_seed_pre_draw_depth(true, false) ||
        game.can_seed_pre_draw_depth(false, false) ||
        game.accepts_full_seeded(2u, false) ||
        !game.accepts_full_seeded(2u, true)) return false;
    game.succeeded(true);
    game.record_source_draw(2u);
    if (game.first_draw() || !game.publishable_full(true, 3u) ||
        game.publishable_full(true, 2u) ||
        !game.absorb_empty_source_draw(3u, true) ||
        game.submitted != 1u || game.postDrawEmptySourceDraws != 1u ||
        !game.publishable_full(true, 4u) ||
        game.absorb_empty_source_draw(5u, true)) return false;
    game.reset();
    if (game.postDrawEmptySourceDraws != 0u ||
        game.absorb_empty_source_draw(0u, false) ||
        game.publishable_full(true, 0u) ||
        !game.first_draw() ||
        !game.absorb_empty_source_draw(0u, true)) return false;
    game.abort();
    return !game.absorb_empty_source_draw(1u, true) &&
        !game.publishable_full(true, 1u);
}
static_assert(leading_game_empty_draw_contract(),
              "Verified full-game Clear must admit leading empty Draw ordinals without a native GPU frame");
int main() {
    return full_game_empty_draw_contract() &&
        leading_game_empty_draw_contract() ? 0 : 1;
}
