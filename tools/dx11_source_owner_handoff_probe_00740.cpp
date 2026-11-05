#include <cassert>
#include <cstdint>
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
int main() {
    constexpr std::uintptr_t game = 0x1111u, aux = 0x2222u;
    using Batch = GameNativeFrameBatch;
    // Known Present owner: auxiliary Draw cannot claim native game/eye output.
    static_assert(Batch::admits_game_source(game, 0u, game));
    static_assert(!Batch::admits_game_source(aux, 0u, game));
    static_assert(Batch::admits_game_source(game, game, aux));
    static_assert(!Batch::admits_game_source(aux, game, game));
    static_assert(!Batch::admits_game_source(0u, 0u, 0u));
    // Startup device unknown: first observed game Draw is provisional.
    static_assert(Batch::admits_game_source(aux, 0u, 0u));
    static_assert(Batch::can_reacquire_full_clear(game, aux, true, true, false, false));
    static_assert(!Batch::can_reacquire_full_clear(game, aux, false, true, false, false));
    static_assert(!Batch::can_reacquire_full_clear(game, aux, true, false, false, false));
    static_assert(!Batch::can_reacquire_full_clear(game, aux, true, true, true, false));
    static_assert(!Batch::can_reacquire_full_clear(game, aux, true, true, false, true));
    static_assert(!Batch::can_reacquire_full_clear(game, game, true, true, false, false));
    static_assert(!Batch::can_reacquire_full_clear(0u, aux, true, true, false, false));
    // New full-clear epoch restores real Draw(0) continuity, with unsupported
    // calls still forcing native fallback rather than losing the D3D9 frame.
    Batch frame{};
    assert(frame.accepts_full_seeded(0u, true));
    frame.succeeded(false);
    frame.record_source_draw(0u);
    assert(frame.accepts_full_seeded(1u, false));
    assert(frame.must_abort_unsupported(true, true));
    frame.abort();
    assert(!frame.publishable_full(true, 1u));
    frame.reset();
    assert(frame.accepts_full_seeded(0u, true));
}
