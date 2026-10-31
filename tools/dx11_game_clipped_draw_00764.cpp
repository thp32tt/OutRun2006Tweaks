#include "../src/vr/d3d11/native_game_scissor_clip.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool clipped(std::uint32_t x, std::uint32_t y,
                       std::uint32_t w, std::uint32_t h,
                       std::int64_t l, std::int64_t t,
                       std::int64_t r, std::int64_t b) {
    return GameNativeScissorClip::excludes_viewport(x,y,w,h,l,t,r,b);
}
static_assert(clipped(100,50,800,600,0,0,100,50));
static_assert(clipped(100,50,800,600,900,0,1000,300));
static_assert(clipped(100,50,800,600,0,650,1000,700));
static_assert(!clipped(100,50,800,600,899,0,1000,300));
static_assert(!clipped(100,50,800,600,0,0,101,51));
static_assert(!clipped(100,50,800,600,0,0,900,650));
static_assert(!clipped(100,50,800,600,100,100,100,200));
static_assert(!clipped(100,50,0,600,0,0,100,50));
static_assert(clipped(UINT32_MAX-30u, UINT32_MAX-20u, 100u, 100u,
                      0,0,UINT32_MAX-31LL,UINT32_MAX-21LL));
// Real full-frame RGB Draw -> scissor-clipped DrawIndexed -> RGB Draw,
// all under one validated full Clear. No duplicate native GPU submission.
constexpr bool interleaved_game_draws() {
    GameNativeFrameBatch frame{};
    if (!frame.accepts_full_on_source_target(0u,true)) return false;
    frame.succeeded(false); frame.record_source_draw(0u);
    if (!frame.absorb_empty_source_draw(1u)) return false;
    if (frame.submitted != 1u || !frame.accepts_full_on_source_target(2u,true))
        return false;
    frame.succeeded(true); frame.record_source_draw(2u);
    return frame.publishable_full(true,3u) && frame.submitted == 2u;
}
constexpr bool leading_clipped_draw() {
    GameNativeFrameBatch frame{};
    if (frame.absorb_empty_source_draw(0u,false)) return false;
    if (!frame.absorb_empty_source_draw(0u,true)) return false;
    if (!frame.accepts_full_on_source_target(1u,true)) return false;
    frame.succeeded(false); frame.record_source_draw(1u);
    return frame.publishable_full(true,2u) && frame.submitted == 1u;
}
constexpr bool rejected_after_gap() {
    GameNativeFrameBatch frame{};
    frame.succeeded(false); frame.record_source_draw(0u);
    return !frame.absorb_empty_source_draw(2u) && !frame.publishable_full(false,3u);
}
static_assert(interleaved_game_draws());
static_assert(leading_clipped_draw());
static_assert(rejected_after_gap());
int main() {
    assert(interleaved_game_draws());
    assert(leading_clipped_draw());
    assert(rejected_after_gap());
}
