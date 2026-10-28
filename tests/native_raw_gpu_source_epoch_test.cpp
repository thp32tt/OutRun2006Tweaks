// Native GPU source Draw -> queued copy -> Present consumption, C++17 regression.
#include "../src/vr/d3d11/native_game_raw_gpu_capture_epoch.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::NativeRawGpuCaptureEpoch;
using outrun::vr::dx11::native_raw_source_color_clear_matches;
using outrun::vr::dx11::native_raw_source_color_write_matches;
int main() {
    // A clipped color Clear on this exact game backbuffer is as capable of
    // superseding a captured native pixel as a full color Clear. Only genuine
    // source ownership and canonical RT identity authorize invalidation.
    constexpr auto cleared = native_raw_source_color_clear_matches(
        0x11u, 0x11u, 0x22u, 0x22u, 3440u, 1440u, 3440u, 1440u);
    static_assert(cleared, "partial source TARGET Clear invalidates GPU evidence");
    static_assert(!native_raw_source_color_clear_matches(
        0x11u, 0x12u, 0x22u, 0x22u, 3440u, 1440u, 3440u, 1440u),
        "foreign owner cannot invalidate source capture");
    static_assert(!native_raw_source_color_clear_matches(
        0x11u, 0x11u, 0x23u, 0x22u, 3440u, 1440u, 3440u, 1440u),
        "offscreen TARGET Clear cannot invalidate backbuffer capture");
    static_assert(!native_raw_source_color_clear_matches(
        0x11u, 0x11u, 0x22u, 0x22u, 1280u, 720u, 3440u, 1440u),
        "mismatched color extent cannot invalidate native capture");
    static_assert(!native_raw_source_color_clear_matches(
        0u, 0x11u, 0x22u, 0x22u, 3440u, 1440u, 3440u, 1440u),
        "unowned diagnostic source cannot invalidate capture");
    // Distinct from TARGET Clear: a successful canonical backbuffer
    // StretchRect/UpdateSurface or ColorFill supersedes prior RAW samples.
    // Empty/failed/foreign/offscreen/mismatched writes cannot revoke evidence.
    constexpr auto copied = native_raw_source_color_write_matches(
        true, true, 0x11u, 0x11u, 0x22u, 0x22u,
        3440u, 1440u, 3440u, 1440u);
    static_assert(copied, "source ColorFill/surface copy must retire RAW RGB");
    static_assert(!native_raw_source_color_write_matches(
        false, true, 0x11u, 0x11u, 0x22u, 0x22u,
        3440u, 1440u, 3440u, 1440u), "failed API cannot retire capture");
    static_assert(!native_raw_source_color_write_matches(
        true, false, 0x11u, 0x11u, 0x22u, 0x22u,
        3440u, 1440u, 3440u, 1440u), "empty fill cannot retire capture");
    static_assert(!native_raw_source_color_write_matches(
        true, true, 0x11u, 0x12u, 0x22u, 0x22u,
        3440u, 1440u, 3440u, 1440u), "foreign writer cannot retire capture");
    static_assert(!native_raw_source_color_write_matches(
        true, true, 0x11u, 0x11u, 0x23u, 0x22u,
        3440u, 1440u, 3440u, 1440u), "offscreen copy cannot retire capture");
    static_assert(!native_raw_source_color_write_matches(
        true, true, 0x11u, 0x11u, 0x22u, 0x22u,
        1280u, 720u, 3440u, 1440u), "wrong-sized destination cannot retire capture");
    NativeRawGpuCaptureEpoch e;
    // Cold-start menu real Draw can queue even at Present serial zero.
    assert(e.can_queue(0u, false));
    e.queued(0u);
    // Repeated game Draws in the same serial cannot silently replace a
    // successful GPU tile; later unsupported/native reset calls do not alter it.
    assert(!e.can_queue(0u, false));
    assert(!e.can_queue(1u, true)); // outstanding async GPU EVENT
    assert(e.consume());
    assert(!e.consume());
    assert(!e.can_queue(0u, false));
    // A new vehicle/race Present may queue a fresh source Draw only after
    // the old GPU copy has retired.
    assert(e.can_queue(1u, false));
    e.queued(1u);
    assert(e.consume());
    // A finished source GPU copy may paint only its matching original
    // Present; a consumed ticket cannot be reused on a second Present.
    e.reset();
    e.queued(7u);
    assert(e.consume_for_present(7u));
    assert(!e.consume_for_present(7u));
    // Once an async copy times out at Present 8, completion at Present 9
    // must discard the old game pixels while preserving in-flight storage.
    e.reset();
    e.queued(8u);
    assert(!e.consume_for_present(9u));
    assert(!e.consume_for_present(8u));
    assert(!e.can_queue(9u, true));
    assert(e.can_queue(9u, false)); // only after GPU fence retired
    e.queued(9u);
    assert(e.consume_for_present(9u));
    // Cropped/dirty-menu Present 41 could not paint a RAW diagnostic tile.
    // The following genuine source Draw safely retires only a completed copy.
    e.reset(); e.queued(41u);
    unsigned polls = 0u;
    using GPU = outrun::vr::dx11::NativeRawGpuWaitResult;
    assert(!e.previous_present_copy(41u));
    assert(e.retire_previous_copy(41u, true, [&] {
        ++polls; return GPU::Complete;
    }) == GPU::Pending);
    assert(polls == 0u && e.consume_for_present(41u));
    e.reset(); e.queued(41u);
    assert(e.previous_present_copy(42u));
    assert(e.retire_previous_copy(42u, true, [&] {
        ++polls; return GPU::Pending;
    }) == GPU::Pending);
    assert(polls == 1u && !e.can_queue(42u, true));
    assert(e.retire_previous_copy(42u, true, [&] {
        ++polls; return GPU::Complete;
    }) == GPU::Complete);
    assert(polls == 2u && !e.consume()); // no stale pixels on later Present
    assert(e.can_queue(42u, false));
    e.queued(42u); assert(e.consume_for_present(42u));
    e.reset(); e.queued(52u);
    assert(e.retire_previous_copy(53u, false, [&] {
        ++polls; return GPU::Complete;
    }) == GPU::Pending);
    assert(polls == 2u); // no outstanding GPU copy, no event query
    // A depth-only/alpha-only first native Draw must not occupy the sole
    // RGB diagnostic capture opportunity for every later Draw this Present.
    e.reset(); e.queued(81u);
    assert(!e.retire_same_present_zero_rgb(82u, true, true, false));
    assert(!e.retire_same_present_zero_rgb(81u, false, true, false));
    assert(!e.retire_same_present_zero_rgb(81u, true, false, false));
    assert(!e.retire_same_present_zero_rgb(81u, true, true, true));
    assert(!e.can_queue(81u, false));
    assert(e.retire_same_present_zero_rgb(81u, true, true, false));
    assert(!e.consume_for_present(81u)); // discarded RGB-inert copy
    assert(e.can_queue(81u, false));
    e.queued(81u); // new native game Draw, same D3D9 Present
    assert(e.consume_for_present(81u));
    assert(!e.can_queue(81u, false)); // one positive pair preserved
    // A canonical backbuffer Clear supersedes even positive native RGB.
    // Same-Present GPU storage cannot be reused until its event completes.
    e.reset(); e.queued(85u);
    assert(cleared && e.invalidate_for_full_source_clear(true));
    assert(e.invalidated_for_full_source_clear());
    assert(!e.consume_for_present(85u));
    assert(!e.can_queue(85u, false));
    assert(e.retire_invalidated_source_clear(true, [&] {
        ++polls; return GPU::Pending;
    }) == GPU::Pending);
    assert(!e.can_queue(85u, false));
    assert(e.retire_invalidated_source_clear(true, [&] {
        ++polls; return GPU::Complete;
    }) == GPU::Complete);
    assert(!e.invalidated_for_full_source_clear());
    assert(e.can_queue(85u, false)); // genuine post-Clear native game Draw
    e.queued(85u);
    assert(e.consume_for_present(85u));
    assert(!e.invalidate_for_full_source_clear(false));
    assert(e.can_queue(85u, false)); // no GPU copy is in flight
    e.queued(85u);
    assert(e.invalidate_for_full_source_clear(false));
    assert(!e.consume_for_present(85u));
    assert(e.can_queue(85u, false));
    // A genuine source Copy/ColorFill also invalidates the queued RGB pair,
    // without freeing its asynchronous GPU resources before the EVENT fence.
    e.reset(); e.queued(854u);
    assert(copied && e.invalidate_for_full_source_clear(true));
    assert(!e.consume_for_present(854u));
    assert(!e.can_queue(854u, true));
    assert(e.retire_invalidated_source_clear(true, [] {
        return GPU::Complete;
    }) == GPU::Complete);
    assert(e.can_queue(854u, false));
    e.queued(854u); assert(e.consume_for_present(854u));
    // Partial menu/HUD TARGET Clears must revoke a captured pixel even if
    // the copy already finished; post-Clear Draws remain eligible without
    // staging resource reuse while an EVENT is still outstanding.
    e.reset(); e.queued(86u);
    assert(cleared && e.invalidate_for_full_source_clear(true));
    assert(!e.consume_for_present(86u));
    assert(!e.can_queue(86u, true));
    assert(e.retire_invalidated_source_clear(true, [&] {
        ++polls; return GPU::Complete;
    }) == GPU::Complete);
    assert(e.can_queue(86u, false));
    e.queued(86u);
    assert(e.consume_for_present(86u));
    // Failed and empty source writes do not supersede a valid native tile.
    // Keep the capture consumable on this SAME original game Present.
    e.reset(); e.queued(855u);
    if (native_raw_source_color_write_matches(
            false, true, 0x11u, 0x11u, 0x22u, 0x22u,
            3440u, 1440u, 3440u, 1440u))
        (void)e.invalidate_for_full_source_clear(true);
    if (native_raw_source_color_write_matches(
            true, false, 0x11u, 0x11u, 0x22u, 0x22u,
            3440u, 1440u, 3440u, 1440u))
        (void)e.invalidate_for_full_source_clear(true);
    assert(e.consume_for_present(855u));
    // An offscreen or foreign Clear never runs the invalidation path.
    e.reset(); e.queued(87u);
    if (native_raw_source_color_clear_matches(
            0x11u, 0x11u, 0x23u, 0x22u, 3440u, 1440u, 3440u, 1440u))
        (void)e.invalidate_for_full_source_clear(true);
    assert(e.consume_for_present(87u));
    e.reset(); // genuine Reset/new D3D9 or D3D11 owner
    assert(e.can_queue(0u, false));
    assert(!e.consume());
    const auto max = (std::numeric_limits<std::uint64_t>::max)();
    // Source serial overflow must fail closed, never release stale samples.
    assert(!e.can_queue(max, true));
    assert(e.can_queue(max, false));
    e.queued(max);
    assert(!e.can_queue(max, false));
    assert(!e.consume_for_present(0u)); // wrapped serial is NOT a match
    return 0;
}
