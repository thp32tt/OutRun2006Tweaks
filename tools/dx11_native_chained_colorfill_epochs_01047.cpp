#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_source_mutation.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::uintptr_t device = 0x1000u, back = 0x2000u;
    GameNativeClearColor seed{};
    seed.record(device, back, 0x11223344u, true, false);
    assert(seed.matches(device, back));
    GameNativeFrameBatch b{};
    // Game menu: first D3D9 Draw -> true full ColorFill, no synthetic Draw.
    assert(b.accepts_full_on_source_target(0u, seed.matches(device,back)));
    b.record_source_draw(0u); b.succeeded(false);
    assert(b.publishable_full(true, 1u));
    assert(b.restart_after_full_color_fill(1u));
    assert(!b.publishable_full(true, 1u));
    assert(b.sourceEpochStart == 1u && b.colorFillEpoch);
    // Car-selection fade: an authentic leading zero-primitive game Draw
    // consumes its original source ordinal and leaves the next GPU RTV seed.
    assert(b.absorb_empty_source_draw(1u, seed.matches(device,back)));
    assert(!b.accepts_full(1u));
    assert(b.accepts_full_on_source_target(2u, seed.matches(device,back)));
    b.record_source_draw(2u); b.succeeded(false);
    assert(b.publishable_full(true, 3u));
    // A second post-Draw full-backbuffer fill replaces ALL prior COLOR.
    assert(b.restart_after_full_color_fill(3u));
    assert(!b.publishable_full(true, 3u));
    assert(b.sourceEpochStart == 3u);
    assert(!b.accepts_full_on_source_target(2u, true));
    assert(b.accepts_full_on_source_target(3u, true));
    assert(!b.accepts_depth(true, false)); // no invented original depth
    b.record_source_draw(3u); b.succeeded(false);
    assert(b.publishable_full(true, 4u));
    // Race transition: third overwrite is again source-proven and contiguous.
    assert(!b.restart_after_full_color_fill(5u)); // skipped D3D9 Draw is poison
    assert(b.publishable_full(true, 4u)); // rejection must not mutate
    assert(b.restart_after_full_color_fill(4u));
    assert(b.sourceEpochStart == 4u);
    assert(b.absorb_empty_source_draw(4u, true));
    b.record_source_draw(5u); b.succeeded(false);
    assert(b.publishable_full(true, 6u));
    assert(!b.publishable_full(true, 7u));

    // Negative/fallback: failed owner, bounded/partial and source gap cannot
    // become an authored whole replacement. Original D3D9 path keeps running.
    assert(!GameNativeSourceMutation::mirrors_full_color_fill(
        true,true,false,true,true,true,true));
    assert(!GameNativeSourceMutation::mirrors_full_color_fill(
        true,true,true,true,false,true,true));
    assert(!GameNativeSourceMutation::mirrors_full_color_fill(
        true,true,true,true,true,false,true));
    assert(!GameNativeSourceMutation::mirrors_full_color_fill(
        true,true,true,true,true,true,false));
    GameNativeFrameBatch missed{};
    missed.record_source_draw(0u); missed.succeeded(false);
    assert(!missed.restart_after_full_color_fill(2u));
    missed.abort();
    assert(!missed.restart_after_full_color_fill(1u));
    GameNativeFrameBatch depth{};
    depth.record_source_draw(0u); depth.succeeded(true);
    assert(!depth.restart_after_full_color_fill(1u));
    GameNativeFrameBatch zclear{};
    zclear.record_source_draw(0u); zclear.succeeded(false);
    zclear.note_full_depth_clear(1.f);
    assert(!zclear.restart_after_full_color_fill(1u));
    GameNativeFrameBatch discontinuity{};
    discontinuity.record_source_draw(0u); discontinuity.succeeded(false);
    assert(discontinuity.restart_after_full_color_fill(1u));
    discontinuity.record_source_draw(1u); discontinuity.succeeded(false);
    discontinuity.abort();
    assert(!discontinuity.restart_after_full_color_fill(2u));
    // Original D3D9 source owner and X8 destination-alpha provenance survive.
    seed.record(device,back,0x00224466u,true,true);
    assert(seed.native_color(device,back,{})[3] == 1.f);
    assert(!seed.matches(device + 1u, back));
    return 0;
}
