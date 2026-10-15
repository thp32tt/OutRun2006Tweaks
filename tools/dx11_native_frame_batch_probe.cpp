#include "native_game_frame_batch.hpp"
#include "native_game_source_mutation.hpp"
#include "native_game_present_region.hpp"
#include <cassert>
#include <cstdint>
#include <initializer_list>
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
using outrun::vr::dx11::live_game_frame::GameNativeSourceMutation;
using outrun::vr::dx11::live_game_frame::GameNativePreDrawFills;
constexpr bool native_predraw_color_fill_regression() {
    GameNativePreDrawFills queue{};
    if (!queue.record(11, 101, 4, 6, 100, 40, 640, 480, 0xff102030u) ||
        !queue.record(11, 101, 8, 10, 120, 60, 640, 480, 0xffabcdefu) ||
        !queue.belongs_to(11, 101) || queue.count != 2u ||
        queue.entries[0].argb != 0xff102030u ||
        queue.entries[1].left != 8 ||
        queue.entries[1].argb != 0xffabcdefu)
        return false;
    // A foreign game device/backbuffer, an invalid tile, or a failed batch
    // cannot masquerade as a complete pre-Draw native menu/race image.
    if (queue.record(22, 101, 1, 1, 3, 3, 640, 480, 0) ||
        queue.record(11, 102, 1, 1, 3, 3, 640, 480, 0) ||
        queue.record(11, 101, -1, 0, 3, 3, 640, 480, 0) ||
        queue.record(11, 101, 1, 1, 641, 3, 640, 480, 0) ||
        queue.count != 2u) return false;
    for (std::uint32_t i = 2; i < GameNativePreDrawFills::kCapacity; ++i)
        if (!queue.record(11, 101, 1, 1, 3, 3, 640, 480, i))
            return false;
    if (queue.count != GameNativePreDrawFills::kCapacity ||
        queue.record(11, 101, 1, 1, 3, 3, 640, 480, 999))
        return false;
    queue.discard(); // new full TARGET Clear / Reset / Present
    return queue.count == 0u && !queue.belongs_to(11, 101) &&
        queue.record(33, 303, 0, 0, 640, 480, 640, 480, 0xff010203u) &&
        queue.belongs_to(33, 303);
}
static_assert(native_predraw_color_fill_regression());
constexpr bool native_non_draw_surface_mutation_regression() {
    using M = GameNativeSourceMutation;
    // Live menu Draw -> ColorFill/StretchRect/UpdateSurface to the seeded
    // game backbuffer -> native batch abort -> untouched D3D9 Present.
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0u);
    if (!frame.publishable_full(true, 1u) ||
        !M::invalidates_full_game_frame(true, true, true, true, false))
        return false;
    frame.abort();
    if (frame.publishable_full(true, 1u) || frame.accepts_full(1u))
        return false;
    // A failed call, foreign device, auxiliary RT or native self-upload
    // must not discard an otherwise valid native menu/race scene.
    return !M::invalidates_full_game_frame(true, false, true, true, false) &&
        !M::invalidates_full_game_frame(true, true, false, true, false) &&
        !M::invalidates_full_game_frame(true, true, true, false, false) &&
        !M::invalidates_full_game_frame(true, true, true, true, true) &&
        !M::invalidates_full_game_frame(false, true, true, true, false);
}
static_assert(native_non_draw_surface_mutation_regression());
// Device GetBackBuffer -> writable CPU LockRect / GDI GetDC -> the same
// canonical native batch observer must abort before altered D3D9 Present.
// Native SYSTEMMEM readback, READONLY, failed acquisition and foreign
// surfaces preserve original game rendering and FFB/input.
constexpr bool native_cpu_surface_write_regression() {
    using M = GameNativeSourceMutation;
    if (!M::cpu_surface_write_possible(true, false, true) ||
        M::cpu_surface_write_possible(true, true, true) ||
        M::cpu_surface_write_possible(false, false, true) ||
        M::cpu_surface_write_possible(true, false, false))
        return false;
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0u);
    if (!frame.publishable_full(true, 1u) ||
        !M::invalidates_full_game_frame(true, true, true, true, false))
        return false;
    frame.abort();
    return !frame.publishable_full(true, 1u) &&
        !M::invalidates_full_game_frame(true, true, false, true, false) &&
        !M::invalidates_full_game_frame(true, true, true, false, false) &&
        !M::invalidates_full_game_frame(true, true, true, true, true);
}
static_assert(native_cpu_surface_write_regression());
// The same seeded menu/vehicle/race native frame can absorb an exact
// whole-backbuffer D3D9 ColorFill as an RTV clear without losing Draw history.
constexpr bool native_full_color_fill_regression() {
    using M = GameNativeSourceMutation;
    if (!M::mirrors_full_color_fill(true, true, true, true, true, true, true) ||
        M::mirrors_full_color_fill(false, true, true, true, true, true, true) ||
        M::mirrors_full_color_fill(true, false, true, true, true, true, true) ||
        M::mirrors_full_color_fill(true, true, false, true, true, true, true) ||
        M::mirrors_full_color_fill(true, true, true, false, true, true, true) ||
        M::mirrors_full_color_fill(true, true, true, true, false, true, true) ||
        M::mirrors_full_color_fill(true, true, true, true, true, false, true) ||
        M::mirrors_full_color_fill(true, true, true, true, true, true, false))
        return false;
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0u);
    if (!frame.publishable_full(true, 1u) ||
        !M::mirrors_full_color_fill(true, true, true, true, true,
                                    !frame.stopped, true)) return false;
    return frame.publishable_full(true, 1u); // No skipped/extra game Draw.
}
static_assert(native_full_color_fill_regression());
// Active menu/car/race Draw -> bounded partial native RTV ColorFill -> later
// Draw/Present continuity; no seed-only partial fill, foreign surface, failed
// D3D9 operation or out-of-bounds write may reuse the native frame.
constexpr bool native_partial_color_fill_regression() {
    using M = GameNativeSourceMutation;
    constexpr auto valid = M::bounded_color_fill_rect(10, 20, 200, 100, 640, 480);
    if (!valid || M::bounded_color_fill_rect(-1, 20, 200, 100, 640, 480) ||
        M::bounded_color_fill_rect(10, 20, 641, 100, 640, 480) ||
        M::bounded_color_fill_rect(10, 20, 10, 100, 640, 480) ||
        M::bounded_color_fill_rect(10, 20, 200, 20, 640, 480) ||
        M::bounded_color_fill_rect(0, 0, 0, 0, 0, 0) ||
        !M::mirrors_partial_color_fill(true, true, true, true, true, valid) ||
        M::mirrors_partial_color_fill(false, true, true, true, true, valid) ||
        M::mirrors_partial_color_fill(true, false, true, true, true, valid) ||
        M::mirrors_partial_color_fill(true, true, false, true, true, valid) ||
        M::mirrors_partial_color_fill(true, true, true, false, true, valid) ||
        M::mirrors_partial_color_fill(true, true, true, true, false, valid) ||
        M::mirrors_partial_color_fill(true, true, true, true, true, false))
        return false;
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0u);
    if (!frame.publishable_full(true, 1u)) return false;
    // ClearView does not add a draw or invalidate the previously seeded Z.
    if (!M::mirrors_partial_color_fill(true, true, true,
            !frame.stopped && frame.submitted != 0u, true, valid))
        return false;
    return frame.publishable_full(true, 1u);
}
static_assert(native_partial_color_fill_regression());

constexpr bool native_partial_target_clear_regression() {
    using M = GameNativeSourceMutation;
    if (!M::mirrors_partial_target_clear(true,true,true,true,true,true,true) ||
        M::mirrors_partial_target_clear(false,true,true,true,true,true,true) ||
        M::mirrors_partial_target_clear(true,false,true,true,true,true,true) ||
        M::mirrors_partial_target_clear(true,true,false,true,true,true,true) ||
        M::mirrors_partial_target_clear(true,true,true,false,true,true,true) ||
        M::mirrors_partial_target_clear(true,true,true,true,false,true,true) ||
        M::mirrors_partial_target_clear(true,true,true,true,true,false,true) ||
        M::mirrors_partial_target_clear(true,true,true,true,true,true,false))
        return false;
    M::TargetClearRect rect{};
    if (!M::clipped_target_clear_rect(-50,20,500,300,
                                     10,30,200,100,640,480,rect) ||
        rect.left != 10 || rect.top != 30 ||
        rect.right != 210 || rect.bottom != 130 ||
        M::clipped_target_clear_rect(500,500,600,600,
                                     10,30,200,100,640,480,rect) ||
        M::clipped_target_clear_rect(10,20,200,120,
                                     600,30,100,100,640,480,rect) ||
        M::clipped_target_clear_rect(10,20,200,120,
                                     0,0,0,480,640,480,rect))
        return false;
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0u);
    if (!frame.publishable_full(true,1u)) return false;
    // Preserve the native DSV and exact source ordinals across a TARGET Clear.
    return M::mirrors_partial_target_clear(
            true,true,true,true,
            !frame.stopped && frame.submitted != 0u,true,true) &&
        frame.submitted == 1u && frame.lastSourceDraw == 0u &&
        frame.depthReady && frame.accepts_full(1u) &&
        frame.publishable_full(true,1u) &&
        M::kMaxPartialTargetClearRects >= 2u;
}
static_assert(native_partial_target_clear_regression());
// Successful multi-rect D3D9 TARGET Clear: only intersecting viewport pixels
 // reach D3D11.1 ClearView. Other well-formed rects are no-ops and cannot
 // cancel native menu/vehicle/race Draw continuity or gamepad/Present.
constexpr bool native_target_clear_disjoint_batch_regression() {
    using M = GameNativeSourceMutation;
    using C = M::TargetClearClip;
    M::TargetClearRect out{};
    std::uint32_t visible = 0u;
    // One rectangle entirely left of the viewport, one intersecting it,
    // one entirely below it. All three were accepted by original D3D9 Clear.
    if (M::classify_target_clear_rect(-100,20,0,120,10,30,200,100,
                                      640,480,out) != C::Empty) return false;
    if (M::classify_target_clear_rect(-100,20,50,120,10,30,200,100,
                                      640,480,out) != C::Pixels ||
        out.left != 10 || out.top != 30 ||
        out.right != 50 || out.bottom != 120) return false;
    ++visible;
    if (M::classify_target_clear_rect(20,200,100,300,10,30,200,100,
                                      640,480,out) != C::Empty) return false;
    if (visible != 1u ||
        M::classify_target_clear_rect(100,50,100,70,10,30,200,100,
                                      640,480,out) != C::Invalid ||
        M::classify_target_clear_rect(100,70,50,80,10,30,200,100,
                                      640,480,out) != C::Invalid ||
        M::classify_target_clear_rect(10,20,20,30,600,30,100,100,
                                      640,480,out) != C::Invalid)
        return false;
    // An all-empty native region batch must return success without a GPU
    // clear; neither that nor a mixed batch retires the same-Present source.
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0u);
    return frame.publishable_full(true,1u) &&
        !frame.stopped && frame.submitted == 1u &&
        frame.depthReady && frame.accepts_full(1u);
}
static_assert(native_target_clear_disjoint_batch_regression());


constexpr bool native_live_partial_depth_clear_regression() {
    using M = GameNativeSourceMutation;
    using Clip = M::TargetClearClip;
    // Live menu/race D32 depth can preserve clipped Z and color+Z regions.
    if (!M::mirrors_partial_depth_clear(true,true,true,true,true,true) ||
        M::mirrors_partial_depth_clear(false,true,true,true,true,true) ||
        M::mirrors_partial_depth_clear(true,false,true,true,true,true) ||
        M::mirrors_partial_depth_clear(true,true,false,true,true,true) ||
        M::mirrors_partial_depth_clear(true,true,true,false,true,true) ||
        M::mirrors_partial_depth_clear(true,true,true,true,false,true) ||
        M::mirrors_partial_depth_clear(true,true,true,true,true,false))
        return false;
    M::TargetClearRect rect{};
    if (M::classify_target_clear_rect(20, 15, 90, 90,
        10, 10, 100, 80, 640, 480, rect) != Clip::Pixels ||
        rect.left != 20 || rect.top != 15 ||
        rect.right != 90 || rect.bottom != 90)
        return false;
    if (M::classify_target_clear_rect(200, 200, 220, 250,
        10, 10, 100, 80, 640, 480, rect) != Clip::Empty ||
        M::classify_target_clear_rect(40, 50, 30, 70,
        10, 10, 100, 80, 640, 480, rect) != Clip::Invalid)
        return false;
    GameNativeFrameBatch scene{};
    scene.succeeded(true);
    scene.record_source_draw(0u);
    const auto before = scene.submitted;
    // Partial Z replaces a region of an existing DSV; no whole depth reset.
    return scene.depthReady && scene.accepts_full(1u) &&
        M::mirrors_partial_depth_clear(true,true,scene.publishable_full(true,1u),
                                       scene.depthReady,true,true) &&
        scene.submitted == before && scene.publishable_full(true,1u);
}
static_assert(native_live_partial_depth_clear_regression());

using outrun::vr::dx11::live_game_frame::GameNativePresentRegion;
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
    // A destructive 4096 -> 8 capacity mutation must not shrink the C++ test
    // loop itself and thereby masquerade as a successful full-frame test.
    assert(GameNativeFrameBatch::kMaxFullFrameDraws == 4096u);
    // 00720 full game native capture must include every original Draw ordinal.
    // A rejected frame must not survive after >8 already-submitted native draws.
    b.reset();
    assert(!b.must_abort_unsupported(false, false));
    assert(!b.must_abort_unsupported(false, true));
    assert(b.must_abort_unsupported(true, false));
    for (std::uint32_t i = 0; i < GameNativeFrameBatch::kMaxDraws + 1u; ++i)
        b.succeeded(false);
    assert(!b.must_abort_unsupported(false, true));
    assert(b.must_abort_unsupported(true, true));
    b.abort();
    assert(!b.publishable_full(true, GameNativeFrameBatch::kMaxDraws + 1u));
    b.reset();
    b.reset();
    assert(b.accepts_full(0u));
    b.succeeded(false); b.record_source_draw(0u);
    assert(!b.publishable_full(true, 2u));
    assert(b.accepts_full(1u));
    b.succeeded(false); b.record_source_draw(1u);
    assert(b.publishable_full(true, 2u));
    assert(!b.publishable_full(false, 2u));
    assert(!b.accepts_full(3u));
    b.abort();
    assert(!b.publishable_full(true, 2u) && !b.accepts_full(2u));
    b.reset();
    for (std::uint32_t i=0; i<GameNativeFrameBatch::kMaxFullFrameDraws; ++i) {
        assert(b.accepts_full(i));
        b.succeeded(false); b.record_source_draw(i);
    }
    assert(b.publishable_full(true, GameNativeFrameBatch::kMaxFullFrameDraws));
    assert(!b.accepts_full(GameNativeFrameBatch::kMaxFullFrameDraws));
    b.reset();
    assert(!b.accepts_full(1u) && !b.publishable_full(true, 0u));
    // A full native game frame covers the original backbuffer: cropping
    // Present must not suppress it or relocate its D3D9 upload origin.
    const GameNativePresentRegion cropped{120, 40, 1200, 760};
    const auto fullCrop = cropped.full_frame_placement(1920, 1080, 1920, 1080);
    assert(fullCrop.valid && fullCrop.left == 0u && fullCrop.top == 0u);
    assert(!cropped.inset_placement(1920, 1080, 1920, 1080, 0).valid);
    assert((GameNativePresentRegion{0, 0, 1920, 1080}
               .full_frame_placement(1920, 1080, 1920, 1080).valid));
    assert(!cropped.full_frame_placement(1920, 1080, 1920, 1079).valid);
    assert(!cropped.full_frame_placement(0, 1080, 0, 1080).valid);
    assert((!GameNativePresentRegion{0, 0, 1921, 1080}
                .full_frame_placement(1920, 1080, 1920, 1080).valid));
    assert((!GameNativePresentRegion{-1, 40, 1200, 760}
                .full_frame_placement(1920, 1080, 1920, 1080).valid));
    assert((!GameNativePresentRegion{120, 40, 120, 760}
                .full_frame_placement(1920, 1080, 1920, 1080).valid));
    return 0;
}
