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
int main() { return full_game_empty_draw_contract() ? 0 : 1; }
