#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::uintptr_t game=0x100u, back=0x200u;
    GameNativeClearColor color{};
    GameNativeFrameBatch batch{};
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back))); // no source Clear
    color.record(game,back,0xff334455u,false);
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back))); // partial
    color.record(game,back,0xff334455u,true);
    assert(batch.accepts_full_seeded(0u,color.matches(game,back))); // real Clear
    assert(!batch.accepts_full_seeded(0u,color.matches(game+1u,back)));
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back+1u)));
    batch.abort(); // pre-first-Draw partial Z or TARGET Clear
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back)));
    batch.reset(); // later successful whole TARGET Clear
    assert(batch.accepts_full_seeded(0u,color.matches(game,back)));
    batch.succeeded(false); batch.record_source_draw(0u);
    assert(batch.accepts_full_seeded(1u,false)); // already seeded, contiguous
    assert(!batch.accepts_full_seeded(2u,true)); // no skipped Draw
    batch.scene_boundary();
    assert(!batch.accepts_full_seeded(1u,true));
    batch.reset(); color.discard();
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back)));
    return 0;
}
