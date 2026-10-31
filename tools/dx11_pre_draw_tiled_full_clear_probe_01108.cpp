// 01108: real D3D9 tiled full TARGET|Z scene admission and stale main-Z
// regression. Native clear coverage must agree across original game source,
// initial D3D11 RTV/D32 seed and later full-frame Draw/DrawIndexed ordinals.
#include "../src/vr/d3d11/native_game_clear_coverage.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_pre_draw_combined_clear.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1,y1,x2,y2; };
template<std::size_t N>
bool full(const std::array<Rect,N>& rects, std::uint32_t w,
          std::uint32_t h) {
    return GameNativeClearCoverage::covers_whole(
        w,h,0u,0u,w,h,static_cast<std::uint32_t>(N),rects.data());
}
}
int main() {
    static_assert(GameNativeClearCoverage::kMaxFullSourceRects ==
                  GameNativePreDrawFills::kMaxPreDrawTargetClearSourceRects);
    std::array<Rect,128> strips{};
    for(std::size_t i=0;i<strips.size();++i)
        strips[i]={static_cast<long>(i*2u),0,
                   static_cast<long>(i*2u+2u),4};
    assert(full(strips,256,4)); // 128 real game D3DRECTs, exact union.
    assert(GameNativeClearCoverage::covers_whole(
        256,4,0,0,256,4,0,(const Rect*)nullptr));
    assert(!GameNativeClearCoverage::covers_whole(
        256,4,1,0,255,4,128,strips.data())); // cropped viewport.
    assert(!GameNativeClearCoverage::covers_whole(
        256,4,0,0,256,4,129,strips.data())); // bounded source.
    auto gap=strips;
    gap[63].x1+=1;
    assert(!full(gap,256,4)); // 1px missing in the native color/Z seed.
    auto inverted=strips;
    inverted[10].x1=inverted[10].x2;
    assert(!full(inverted,256,4));
    auto outside=strips;
    outside[0].x1=-60; outside[127].x2=300;
    assert(full(outside,256,4)); // original D3D9 clipped source.
    std::array<Rect,17> seventeen{};
    for(std::size_t i=0;i<seventeen.size();++i)
        seventeen[i]={static_cast<long>(i*2),0,
                      static_cast<long>(i*2+2),4};
    assert(full(seventeen,34,4));
    GameNativeFrameBatch batch{};
    // Positive native full-size first-Draw seed, then exact source ordinal.
    const bool originalTargetSeed=full(seventeen,34,4);
    assert(batch.accepts_full_seeded(0u,originalTargetSeed));
    assert(batch.absorb_empty_source_draw(0u,originalTargetSeed));
    assert(batch.accepts_full_seeded(1u,originalTargetSeed));
    batch.record_source_draw(1u);batch.succeeded(true);
    assert(batch.publishable_full(true,2u));
    // Target-only full game Clear after an earlier depth Draw retains real
    // D3D9 Z, but the newly reset native DSV does not. Hold before Draw.
    batch.reset();
    batch.preserve_depth_provenance_after_target_seed(true,false);
    assert(batch.awaitingColorFillDepthReset);
    assert(!batch.accepts_full_seeded(0u,true));
    assert(!batch.absorb_empty_source_draw(0u,true));
    assert(!batch.resume_after_game_full_depth_clear(1u,0.3f));
    assert(!batch.resume_after_game_full_depth_clear(0u,-0.1f));
    assert(batch.resume_after_game_full_depth_clear(0u,0.3f));
    batch.note_full_depth_clear(0.3f);
    assert(batch.accepts_full_seeded(0u,true));
    assert(batch.depth_clear_value(false)==0.3f);
    batch.reset();
    batch.preserve_depth_provenance_after_target_seed(true,true);
    assert(!batch.awaitingColorFillDepthReset); // TARGET|Z clear owns Z.
    assert(batch.accepts_full_seeded(0u,true));
    batch.reset();
    batch.preserve_depth_provenance_after_target_seed(false,false);
    assert(batch.accepts_full_seeded(0u,true)); // no preceding source Z.
    // Too many partial tiles are NOT a substitute for recognizing a full
    // authentic 17+ rectangle game Clear before the first native Draw.
    GameNativePreDrawFills color{};
    assert(color.record_target_clear(
        4,9,34,4,0,0,34,4,17,seventeen.data(),0xff456789u));
    assert(color.replay_ready(4,9,34,4));
    GameNativePreDrawDepth z{};
    assert(z.record(4,9,12,256,4,0,0,256,4,128,strips.data(),0.25f));
    assert(z.replay_ready(4,9,12,256,4));
    assert(!z.replay_ready(4,9,99,256,4)); // foreign main depth.
}
