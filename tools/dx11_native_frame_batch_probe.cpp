#include "native_game_frame_batch.hpp"
#include <cassert>
#include <cstdint>
#include <initializer_list>
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
int main() {
    GameNativeFrameBatch b{};
    assert(!b.accepts(0,2,false) && b.accepts(2,2,false));
    assert(b.first_draw() && b.clear_depth());
    b.succeeded(false);
    assert(!b.first_draw() && b.clear_depth() && !b.accepts(3,2,false));
    b.reset();
    assert(!b.accepts(4,5,true) && b.accepts(5,5,true));
    b.succeeded(false);
    assert(b.clear_depth());
    b.succeeded(true);
    assert(!b.clear_depth());
    b.reset();
    for (std::uint32_t i=5; i<5+GameNativeFrameBatch::kMaxDraws; ++i) {
        assert(b.accepts(i,5,true));
        b.succeeded(i==6u);
    }
    assert(!b.accepts(13,5,true) && b.submitted==8u && !b.clear_depth());
    b.reset();
    assert(b.accepts(256u,256u,true));
    assert(b.accepts(263u,256u,true));
    assert(!b.accepts(264u,256u,true));
    assert(!b.accepts(400u,256u,true));
    assert(!b.accepts(255u,256u,true));
    b.reset();
    assert(b.accepts_depth(true,false) && b.accepts_depth(true,true));
    b.succeeded(true,false);
    assert(b.accepts_depth(true,false));
    assert(!b.accepts_depth(true,true));
    assert(b.accepts_depth(false,true));
    b.reset();
    b.succeeded(true,true);
    assert(b.accepts_depth(true,true) && !b.accepts_depth(true,false));
    // 00675: full game scene coverage, including calls beyond the old 64
    // probe window. 257 is intentionally non-power-of-two.
    for (std::uint32_t population : {3u, 65u, 128u, 257u, 4096u}) {
        std::uint32_t cursor = 0u;
        for (std::uint32_t candidate = 0u; candidate < population; ++candidate) {
            assert(cursor == candidate);
            assert(b.first_draw() && b.accepts(cursor, cursor, false));
            cursor = GameNativeFrameBatch::next_probe_slot(cursor, population);
        }
        assert(cursor == 0u);
        assert(GameNativeFrameBatch::next_probe_slot(population + 20u, population) == 0u);
        assert(GameNativeFrameBatch::next_probe_slot(9u, 0u) == 0u);
    }
    assert(GameNativeFrameBatch::next_probe_slot(0xffffffffu, 0xffffffffu) == 0u);
    b.reset();
    b.succeeded(true); b.abort();
    assert(!b.accepts(1,0,true));
    b.reset();
    assert(b.accepts(0,0,true) && b.first_draw() && b.clear_depth());
    return 0;
}
