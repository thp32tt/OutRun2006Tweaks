#include "../src/vr/d3d11/native_game_clear_coverage.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
struct Rect { int x1,y1,x2,y2; };
constexpr bool test() {
    constexpr Rect full{0,0,640,480}, half{0,0,640,240};
    constexpr Rect vertical[]{{0,0,320,480},{320,0,640,480}};
    constexpr Rect horizontal[]{{0,0,640,240},{0,240,640,480}};
    constexpr Rect tile[]{{0,0,320,240},{320,0,640,240},{0,240,320,480},{320,240,640,480}};
    constexpr Rect hole[]{{0,0,319,480},{320,0,640,480}};
    // D3D9 clamps Clear rectangles to the target viewport, so a slightly
    // out-of-bounds rectangle can still cover the entire game backbuffer.
    // Reversed extents remain invalid and must never seed a native frame.
    constexpr Rect clipped{-1,0,640,480};
    constexpr Rect reversed{320,0,319,480};
    using C=GameNativeClearCoverage;
    if (!C::covers_whole(640,480,0,0,640,480,0,static_cast<const Rect*>(nullptr)) ||
        !C::covers_whole(640,480,0,0,640,480,1,&full) ||
        !C::covers_whole(640,480,0,0,640,480,2,vertical) ||
        !C::covers_whole(640,480,0,0,640,480,2,horizontal) ||
        !C::covers_whole(640,480,0,0,640,480,4,tile) ||
        !C::covers_whole(640,480,0,0,640,480,1,&clipped)) return false;
    if (C::covers_whole(640,480,0,0,640,480,2,hole) ||
        C::covers_whole(640,480,0,0,640,480,1,&half) ||
        C::covers_whole(640,480,1,0,639,480,1,&full) ||
        C::covers_whole(640,480,0,0,640,480,1,&reversed) ||
        C::covers_whole(640,480,0,0,640,480,1,static_cast<const Rect*>(nullptr))) return false;
    // 01108 raised the authentic source rectangle bound from 16 to 128.
    // A 17-strip game Clear is now positive coverage; a 129-region source
    // is rejected by its real count, not by reading past a single Rect.
    std::array<Rect, 17> strips{};
    for (int i = 0; i < 17; ++i)
        strips[static_cast<std::size_t>(i)] = {
            640 * i / 17, 0, 640 * (i + 1) / 17, 480};
    if (!C::covers_whole(640,480,0,0,640,480,
                         17,strips.data())) return false;
    std::array<Rect, 129> overLimit{};
    for (auto& r : overLimit) r = full;
    if (C::covers_whole(640,480,0,0,640,480,
                        129,overLimit.data())) return false;
    // The live Clear hook resets an aborted pre-Clear scene only when
    // full coverage is proven; post-Clear native Draw begins at ordinal 0.
    GameNativeFrameBatch batch{};
    batch.succeeded(false);
    batch.record_source_draw(0);
    batch.scene_boundary();
    if (batch.publishable(true)) return false;
    batch.reset();
    if (!batch.accepts_full(0)) return false;
    batch.succeeded(false);
    batch.record_source_draw(0);
    if (!batch.publishable_full(true,1)) return false;
    batch.scene_boundary();
    if (batch.publishable_full(true,1)) return false;
    GameNativeClearColor color{};
    color.record(1,2,0xff0080ffu,true);
    const auto c=color.native_color(1,2,{0,0,0,0});
    return c[0]==0.0f && c[1]>0.0f && c[2]==1.0f;
}
static_assert(test(), "game tiled clear -> post-Clear native Draw or safe abort");
int main(){assert(test());}
