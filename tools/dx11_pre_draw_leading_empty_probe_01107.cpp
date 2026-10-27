// Real D3D9 menu/car/race ordinal bridge: leading zero-pixel Draw calls
// may precede authentic TARGET|Z|STENCIL and separate Z partial Clears.
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_main_stencil_clear.hpp"
#include "../src/vr/d3d11/native_game_pre_draw_combined_clear.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1, y1, x2, y2; };
constexpr std::size_t W = 12u, H = 8u;
using Pixels = std::array<std::uint32_t,W*H>;
using Depth = std::array<float,W*H>;
void paint(Pixels& c, Depth& d, Rect r, std::uint32_t argb, float z) {
    for (long y=r.y1; y<r.y2; ++y)
        for (long x=r.x1; x<r.x2; ++x) {
            c[std::size_t(y)*W+std::size_t(x)]=argb;
            d[std::size_t(y)*W+std::size_t(x)]=z;
        }
}
void compare(const GameNativePreDrawFills& fills,
             const GameNativePreDrawDepth& tiles,
             const Pixels& original, const Depth& originalZ) {
    assert(fills.replay_ready(4,9,W,H));
    assert(tiles.replay_ready(4,9,12,W,H));
    Pixels native{};native.fill(0xff000000u);
    Depth nativeZ{};nativeZ.fill(1.f);
    for (std::uint32_t i=0;i<fills.count;++i) {
        const auto& f=fills.entries[i];
        for (auto y=f.top;y<f.bottom;++y)
            for (auto x=f.left;x<f.right;++x)
                native[std::size_t(y)*W+std::size_t(x)]=f.argb;
    }
    for (std::uint32_t i=0;i<tiles.count;++i) {
        const auto& f=tiles.tiles[i];
        for (auto y=f.top;y<f.bottom;++y)
            for (auto x=f.left;x<f.right;++x)
                nativeZ[std::size_t(y)*W+std::size_t(x)]=f.z;
    }
    assert(native==original && nativeZ==originalZ);
}
} // namespace
int main() {
    GameNativeFrameBatch frame{};
    frame.note_full_depth_clear(1.f);
    assert(frame.before_first_native_raster(0u));
    assert(frame.absorb_empty_source_draw(0u,true));
    assert(frame.absorb_empty_source_draw(1u,true));
    assert(frame.before_first_native_raster(2u));
    assert(!frame.before_first_native_raster(3u)); // unobserved Draw gap
    assert(frame.can_seed_pre_draw_depth_at_ordinal(true,2u));
    assert(!frame.can_seed_pre_draw_depth_at_ordinal(false,2u)); // wrong RT
    assert(GameNativeMainStencilClear::may_ignore_pre_draw(
        true,true,true,frame.before_first_native_raster(2u),true));
    GameNativePreDrawFills colors{};
    GameNativePreDrawDepth depths{};
    Pixels source{}; source.fill(0xff000000u);
    Depth sourceZ{}; sourceZ.fill(1.f);
    constexpr std::uint32_t A=0xff12ab35u,B=0xff8b2345u;
    const Rect a{0,0,8,6},b{3,2,11,8};
    assert(GameNativePreDrawCombinedClear::record(
        colors,depths,4,9,12,W,H,0,0,W,H,1,&a,A,0.7f));
    paint(source,sourceZ,a,A,0.7f);
    assert(GameNativePreDrawCombinedClear::record(
        colors,depths,4,9,12,W,H,0,0,W,H,1,&b,B,0.35f));
    paint(source,sourceZ,b,B,0.35f);
    compare(colors,depths,source,sourceZ);
    // D3D9 Z-only rect after the leading no-op Draws retains the old color.
    const Rect zOnly{1,1,3,3};
    assert(depths.record(4,9,12,W,H,0,0,W,H,1,&zOnly,0.25f));
    for (long y=zOnly.y1;y<zOnly.y2;++y)
        for (long x=zOnly.x1;x<zOnly.x2;++x)
            sourceZ[std::size_t(y)*W+std::size_t(x)]=0.25f;
    compare(colors,depths,source,sourceZ);
    // No partial transaction if a foreign main-Z owner is bound.
    const auto saved=depths;
    assert(!GameNativePreDrawCombinedClear::record(
        colors,depths,4,9,99,W,H,0,0,W,H,1,&a,A,0.1f));
    assert(depths.count==saved.count);
    compare(colors,depths,source,sourceZ);
    // After a real GPU Draw, pre-Draw Clear admission MUST close.
    frame.record_source_draw(2u);
    frame.succeeded(true);
    assert(!frame.before_first_native_raster(3u));
    assert(!frame.can_seed_pre_draw_depth_at_ordinal(true,3u));
    // A full ColorFill can start an absolute source epoch at 7; no
    // source Draw in the NEW epoch is not the same as global ordinal zero.
    GameNativeFrameBatch second{};
    second.sourceEpochStart=7u;
    second.note_full_depth_clear(1.f);
    assert(second.before_first_native_raster(7u));
    assert(second.can_seed_pre_draw_depth_at_ordinal(true,7u));
    assert(second.absorb_empty_source_draw(7u,true));
    assert(second.before_first_native_raster(8u));
    assert(!second.before_first_native_raster(9u));
    second.abort();
    assert(!second.before_first_native_raster(8u));
}
