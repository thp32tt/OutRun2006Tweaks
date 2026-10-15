#include "../src/vr/d3d11/native_game_clear_coverage.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
struct Rect { std::int32_t x1, y1, x2, y2; };
constexpr bool full(const Rect* r, std::uint32_t n) {
    return GameNativeClearCoverage::covers_whole(
        640u, 480u, 0u, 0u, 640u, 480u, n, r);
}
constexpr bool coverage_contract() {
    const Rect oversize[]{{-16,-48,700,520}};
    const Rect verticalTiles[]{{-80,-90,320,550},{320,-90,700,550}};
    const Rect horizontalTiles[]{{-20,-30,700,240},{-20,240,700,540}};
    const Rect unrelated[]{{-1000,-1000,-900,-900},{0,0,640,480}};
    const Rect incomplete[]{{-16,-16,319,490},{320,-16,700,490}};
    const Rect badOrder[]{{0,0,640,480},{640,400,10,479}};
    const Rect outside[]{{-100,-100,-1,-1}};
    if (!full(nullptr,0u) || !full(oversize,1u) ||
        !full(verticalTiles,2u) || !full(horizontalTiles,2u) ||
        !full(unrelated,2u)) return false;
    if (full(incomplete,2u) || full(badOrder,2u) || full(outside,1u) ||
        full(nullptr,1u)) return false;
    if (GameNativeClearCoverage::covers_whole(
            640u,480u,0u,0u,639u,480u,1u,oversize)) return false;
    if (GameNativeClearCoverage::covers_whole(
            640u,480u,0u,0u,640u,480u,17u,oversize)) return false;
    return true;
}
constexpr bool native_game_draw_contract() {
    constexpr Rect oversize[]{{-16,-48,700,520}};
    GameNativeClearColor color{};
    GameNativeFrameBatch batch{};
    constexpr std::uintptr_t game=0x10u, backbuffer=0x20u;
    color.record(game,backbuffer,0xff112233u,full(oversize,1u));
    if (!color.matches(game,backbuffer) ||
        !batch.accepts_full_on_source_target(0u,color.matches(game,backbuffer)))
        return false;
    batch.succeeded(false); batch.record_source_draw(0u);
    if (!batch.accepts_full_on_source_target(1u,color.matches(game,backbuffer)))
        return false; // The real DrawIndexed after Draw shares the Clear seed.
    batch.succeeded(false); batch.record_source_draw(1u);
    if (!batch.publishable_full(true,2u)) return false;
    batch.scene_boundary(); // Partial next Clear still fails closed.
    if (batch.publishable_full(true,2u)) return false;
    color.record(game,backbuffer,0xff112233u,false);
    return !color.matches(game,backbuffer);
}
static_assert(coverage_contract(), "D3D9 clipped Clear union/fallback");
static_assert(native_game_draw_contract(), "live Clear->Draw/Indexed batch");
int main() {
    assert(coverage_contract());
    assert(native_game_draw_contract());
}
