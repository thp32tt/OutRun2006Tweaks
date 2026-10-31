#include <cassert>
#include <cstdint>
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
int main() {
    using Batch = GameNativeFrameBatch;
    constexpr std::uintptr_t game = 0x1111u, auxiliary = 0x2222u;
    // Live menu/race Draws survive an unrelated D3D9 device Reset.
    static_assert(Batch::reset_belongs_to_game_source(game, game, game));
    static_assert(!Batch::reset_belongs_to_game_source(auxiliary, game, game));
    static_assert(!Batch::reset_belongs_to_game_source(auxiliary, game, 0u));
    // A Draw-less frame still binds to the last actual game Present.
    static_assert(Batch::reset_belongs_to_game_source(game, 0u, game));
    static_assert(!Batch::reset_belongs_to_game_source(auxiliary, 0u, game));
    // A newly acquired game source (after a full game Clear) supersedes the
    // older Present owner; its real Reset must invalidate native resources.
    static_assert(Batch::reset_belongs_to_game_source(auxiliary, auxiliary, game));
    static_assert(!Batch::reset_belongs_to_game_source(game, auxiliary, game));
    // Unknown startup: Reset can safely retire unknown speculative state.
    static_assert(Batch::reset_belongs_to_game_source(game, 0u, 0u));
    static_assert(!Batch::reset_belongs_to_game_source(0u, 0u, 0u));
    static_assert(!Batch::reset_belongs_to_game_source(0u, game, game));
    Batch batch{};
    assert(batch.accepts_full_seeded(0u, true));
    batch.succeeded(false);
    batch.record_source_draw(0u);
    // The foreign Reset gate does not modify this active game Draw batch.
    if (Batch::reset_belongs_to_game_source(auxiliary, game, game))
        batch.reset();
    assert(batch.publishable_full(true, 1u));
    // The legitimate owner's Reset still invalidates speculative output.
    if (Batch::reset_belongs_to_game_source(game, game, game))
        batch.reset();
    assert(!batch.publishable_full(true, 1u));
}
