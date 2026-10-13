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
    assert(!b.accepts(7u, 5u, true)); // Reject missing ordinal 6.
    assert(b.accepts(6u, 5u, true));
    b.succeeded(true);
    assert(!b.clear_depth());
    assert(!b.accepts(8u, 5u, true)); // Later in window is still a gap.
    assert(b.accepts(7u, 5u, true));
    b.reset();
    for (std::uint32_t i=5; i<5+GameNativeFrameBatch::kMaxDraws; ++i) {
        assert(b.accepts(i,5,true));
        b.succeeded(i==6u);
    }
    assert(!b.accepts(13,5,true) && b.submitted==8u && !b.clear_depth());
    b.reset();
    assert(b.accepts(256u,256u,true));
    assert(!b.accepts(263u,256u,true)); // In range but not contiguous.
    for (std::uint32_t i=256u; i<264u; ++i) {
        assert(b.accepts(i,256u,true));
        b.succeeded(false);
    }
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
    // End the previous depth-positive case before testing empty rotating frames.
    b.reset();
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
    // Real game call positions are independent from the eligible FVF cursor.
    // A skipped unsupported Draw between native Draws invalidates the inset.
    assert(b.accepts_source_draw(400u, true));
    b.record_source_draw(400u);
    b.succeeded(false);
    assert(b.accepts_source_draw(401u, true));
    assert(!b.accepts_source_draw(402u, true));
    assert(b.accepts_source_draw(402u, false)); // Single Draw remains independent.
    assert(b.publishable(true));
    b.abort();
    assert(!b.accepts_source_draw(401u, true));
    assert(!b.publishable(true));  // A prior GPU Draw cannot leak to Present.
    b.reset();
    assert(!b.publishable(true) && !b.publishable(false));
    assert(b.accepts_source_draw(0u, true));
    b.record_source_draw(0u);
    b.succeeded(true);
    assert(b.accepts_source_draw(1u, true));
    b.record_source_draw(1u);
    b.succeeded(false);
    assert(b.publishable(true));
    assert(!b.publishable(false));
    b.reset();
    assert(b.first_draw() && b.accepts_source_draw(1500u, true));
    b.record_source_draw(1500u);
    b.succeeded(false);
    assert(!b.accepts_source_draw(1502u, true)); // Missed game draw.
    assert(!b.accepts_source_draw(1499u, true)); // Reordered game draw.
    return 0;
}
