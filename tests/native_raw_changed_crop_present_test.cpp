// Authentic pre/post native Draw pixels must remain visible in even the
// smallest supported D3D9 source Present crop. No full-frame promotion.
#include "../src/vr/d3d11/native_game_raw_partial_present_tile.hpp"
#include "../src/vr/d3d11/native_game_raw_color_transport.hpp"
#include "../src/vr/d3d11/native_game_raw_present_coverage.hpp"
#include "../src/vr/d3d11/native_game_raw_upload_transaction.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11;
constexpr bool native_raw_changed_crop_regression() {
    NativeRawPresentTile base{}, moved{};
    if (!native_raw_partial_present_tile(
            1920, 1080, 700, 300, 748, 348, 256, 144, base) ||
        base.copyWidth != 32u || base.copyHeight != 32u ||
        base.sourceX != 112u || base.sourceY != 56u)
        return false;
    // A source-authentic game Draw changed the far GPU bottom/right corner:
    // old centered 32x32 subsection would incorrectly report no visible Draw.
    if (!native_raw_retarget_present_tile(
            base, 256, 144, 250, 130, moved) ||
        moved.sourceX != 224u || moved.sourceY != 112u ||
        moved.destinationX != base.destinationX ||
        moved.destinationY != base.destinationY ||
        250u - moved.sourceX >= moved.copyWidth ||
        130u - moved.sourceY >= moved.copyHeight)
        return false;
    // Changed source pixel survives magenta label even at the actual border.
    if (native_raw_present_border_pixel(moved, 250, 130, true) ||
        !native_raw_present_border_pixel(moved, 224, 112, false) ||
        native_raw_present_border_pixel(moved, 233, 121, false) ||
        native_raw_present_border_pixel(moved, 223, 112, false))
        return false;
    if (!native_raw_retarget_present_tile(
            base, 256, 144, 0, 0, moved) ||
        moved.sourceX || moved.sourceY ||
        native_raw_present_border_pixel(moved, 0, 0, true))
        return false;
    // Previously a small full native-game repaint was rejected by the
    // legacy 40px displaced-inset margin, before source-aligned RGB batching.
    // Only the caller-proven canonical Draw/Present path can use this tile.
    NativeRawPresentTile small{};
    if (!native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 724, 324, 256, 144, small) ||
        small.copyWidth != 24u || small.copyHeight != 24u ||
        small.sourceX != 116u || small.sourceY != 60u ||
        small.destinationX != 700 || small.destinationY != 300 ||
        !native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 739, 332, 256, 144, small) ||
        small.copyWidth != 39u || small.copyHeight != 32u ||
        native_raw_verified_small_source_present_tile(
            false, 1920, 1080, 700, 300, 724, 324, 256, 144, small) ||
        !native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 723, 324, 256, 144, small) ||
        native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 740, 340, 256, 144, small) ||
        !native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 724, 324, 23, 144, small) ||
        native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 1900, 1060, 1921, 1081, 256, 144, small))
        return false;
    // The canonical Draw/Present identity path may publish a one-pixel
    // original game source crop; displaced RAW still rejects this size.
    NativeRawPresentTile tiny{}, clipped{};
    if (!native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 701, 301, 256, 144, tiny) ||
        tiny.copyWidth != 1u || tiny.copyHeight != 1u ||
        tiny.sourceX != 127u || tiny.sourceY != 71u ||
        !native_raw_source_capture_clip_tile(
            573u, 229u, 256u, 144u, 1920u, 1080u,
            1920u, 1080u, 700, 300, 701, 301, clipped) ||
        clipped.sourceX != 127u || clipped.sourceY != 71u ||
        clipped.destinationX != 700 || clipped.destinationY != 300 ||
        native_raw_verified_small_source_present_tile(
            false, 1920, 1080, 700, 300, 701, 301, 256, 144, tiny) ||
        native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 740, 340, 256, 144, tiny) ||
        native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 700, 301, 256, 144, tiny) ||
        native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 701, 301, 0, 144, tiny) ||
        native_raw_source_capture_clip_tile(
            573u, 229u, 256u, 144u, 1919u, 1080u,
            1920u, 1080u, 700, 300, 701, 301, clipped))
        return false;
    // A source-aligned 1px dirty Present must bypass legacy 24px displaced
    // inset placement; unverified/ordinary dirty diagnostic retains it.
    if (native_raw_requires_legacy_dirty_placement(true, false, true) ||
        !native_raw_requires_legacy_dirty_placement(true, false, false) ||
        native_raw_requires_legacy_dirty_placement(false, false, false) ||
        native_raw_requires_legacy_dirty_placement(true, true, false))
        return false;
    // Genuine dirty Present members may also completely cover a tiny crop.
    // A bounding rectangle containing a hole must never authorize painting.
    NativeRawPresentDirtyRegion tinyDirty{};
    tinyDirty.headerVerified = true;
    tinyDirty.count = 2u;
    tinyDirty.boundLeft = 700;
    tinyDirty.boundTop = 300;
    tinyDirty.boundRight = 702;
    tinyDirty.boundBottom = 301;
    tinyDirty.rectangles[0] = {700, 300, 701, 301};
    tinyDirty.rectangles[1] = {701, 300, 702, 301};
    if (!native_raw_dirty_covers_small_source_crop(
            1920, 1080, 700, 300, 702, 301, tinyDirty) ||
        native_raw_dirty_covers_small_source_crop(
            1920, 1080, 700, 300, 703, 301, tinyDirty))
        return false;
    tinyDirty.rectangles[1] = {702, 300, 703, 301};
    tinyDirty.boundRight = 703;
    if (native_raw_dirty_covers_small_source_crop(
            1920, 1080, 700, 300, 703, 301, tinyDirty))
        return false;
    tinyDirty.rectangles[1] = {701, 300, 702, 301};
    tinyDirty.boundRight = 703; // forged rcBound must fail
    if (native_raw_dirty_covers_small_source_crop(
            1920, 1080, 700, 300, 702, 301, tinyDirty))
        return false;
    // Genuine smaller game-created GPU targets share their own exact pixels.
    if (!native_raw_verified_small_source_present_tile(
            true, 2, 2, 0, 0, 1, 1, 2, 2, tiny) ||
        tiny.copyWidth != 1 || tiny.copyHeight != 1)
        return false;
    // Invalid/invented source identity or dimensions must fail closed.
    NativeRawPresentTile bad = base;
    if (native_raw_retarget_present_tile(
            base, 256, 144, 256, 130, moved) ||
        native_raw_retarget_present_tile(
            base, 256, 144, 250, 144, moved))
        return false;
    bad.sourceX = 255;
    if (native_raw_retarget_present_tile(
            bad, 256, 144, 5, 5, moved))
        return false;
    bad = base;
    bad.copyWidth = 0;
    if (native_raw_retarget_present_tile(
            bad, 256, 144, 5, 5, moved))
        return false;
    return true;
}
static_assert(native_raw_changed_crop_regression(), "RAW live GPU pixels cannot disappear behind crop/label");

bool native_raw_tiny_rgb_source_upload_regression() {
    // Model the fence-completed GPU PRE/POST data of a 2x2 game color target.
    // Only a single original D3D9 source pixel acquired authentic GPU RGB.
    const std::array<std::uint8_t, 16> before{};
    std::array<std::uint8_t, 16> after{};
    after[0] = 21u; after[1] = 43u; after[2] = 65u; after[3] = 87u;
    static NativeRawChangedPixelWindow gpu{};
    gpu.capture(before.data(), 8u, after.data(), 8u, 2u, 2u);
    NativeRawPresentDirtyRegion sourceRepaint{};
    NativeRawPresentTile clipped{};
    if (!native_raw_verified_full_source_crop_region(
            true, 2u, 2u, 0, 0, 1, 1, sourceRepaint) ||
        !native_raw_source_capture_clip_tile(
            0u, 0u, 2u, 2u, 2u, 2u, 2u, 2u,
            0, 0, 1, 1, clipped))
        return false;
    NativeRawSourceIslandBatch batch{};
    if (!batch.append(2u, 2u, sourceRepaint, clipped, gpu, false, true) ||
        batch.count != 1u || batch.rgbPixels[0] != 1u ||
        batch.tiles[0].copyWidth != 1u ||
        batch.tiles[0].copyHeight != 1u ||
        batch.tiles[0].destinationX != 0 ||
        batch.tiles[0].destinationY != 0)
        return false;
    std::array<std::uint8_t, 16> destination{};
    if (!native_raw_copy_present_island(
            destination.data(), 8u, before.data(), 8u, after.data(), 8u,
            2u, 2u, batch.tiles[0], NativeRawColorByteOrder::Rgba, false) ||
        destination[0] != 65u || destination[1] != 43u ||
        destination[2] != 21u || destination[3] != 87u ||
        destination[4] != 0u || destination[8] != 0u)
        return false;
    // An unchanged RGB source pixel never authorizes any D3D9 upload.
    after = before;
    gpu.capture(before.data(), 8u, after.data(), 8u, 2u, 2u);
    NativeRawSourceIslandBatch invalid{};
    return !invalid.append(
        2u, 2u, sourceRepaint, clipped, gpu, false, true);
}

// A source-authenticated DX11 Draw can change a 1px menu island within
// a FULL-SIZE D3D9 Present whose dirty RGNDATA paints only that single pixel.
// The displaced RAW diagnostic cannot fit here. Preserve exact coordinates,
// real GPU byte transport, and never allow foreign/forged/holey regions.
bool native_raw_large_crop_sparse_dirty_source_regression() {
    NativeRawPresentDirtyRegion repaint{};
    repaint.headerVerified = true;
    repaint.count = 1u;
    repaint.boundLeft = 700; repaint.boundTop = 300;
    repaint.boundRight = 701; repaint.boundBottom = 301;
    repaint.rectangles[0] = {700, 300, 701, 301};
    if (!native_raw_source_only_dirty_crop_can_defer_placement(
            true, 1920u, 1080u, 1920u, 1080u,
            0, 0, 1920, 1080, repaint) ||
        native_raw_source_only_dirty_crop_can_defer_placement(
            false, 1920u, 1080u, 1920u, 1080u,
            0, 0, 1920, 1080, repaint) ||
        native_raw_source_only_dirty_crop_can_defer_placement(
            true, 1280u, 720u, 1920u, 1080u,
            0, 0, 1920, 1080, repaint) ||
        native_raw_source_only_dirty_crop_can_defer_placement(
            true, 1920u, 1080u, 1920u, 1080u,
            800, 300, 900, 400, repaint))
        return false;
    const std::array<std::uint8_t, 16> before{};
    std::array<std::uint8_t, 16> after{};
    after[0] = 4u; after[1] = 5u; after[2] = 6u; after[3] = 7u;
    static NativeRawChangedPixelWindow delta{};
    delta.capture(before.data(), 8u, after.data(), 8u, 2u, 2u);
    NativeRawPresentTile source{};
    if (!native_raw_source_capture_clip_tile(
            700u, 300u, 2u, 2u, 1920u, 1080u,
            1920u, 1080u, 0, 0, 1920, 1080, source))
        return false;
    NativeRawSourceIslandBatch batch{};
    if (!batch.append(1920u, 1080u, repaint, source, delta,
                      false, true) ||
        batch.count != 1u || batch.rgbPixels[0] != 1u ||
        batch.tiles[0].sourceX != 0u || batch.tiles[0].sourceY != 0u ||
        batch.tiles[0].copyWidth != 1u || batch.tiles[0].copyHeight != 1u ||
        batch.tiles[0].destinationX != 700 ||
        batch.tiles[0].destinationY != 300)
        return false;
    std::array<std::uint8_t, 16> destination{};
    if (!native_raw_copy_present_island(
            destination.data(), 8u, before.data(), 8u, after.data(), 8u,
            2u, 2u, batch.tiles[0], NativeRawColorByteOrder::Rgba, false) ||
        destination[0] != 6u || destination[1] != 5u ||
        destination[2] != 4u || destination[3] != 7u ||
        destination[4] != 0u || destination[8] != 0u)
        return false;
    // A forged region bound invalidates every member, not just the
    // upload candidate, and unchanged native RGB never starts a batch.
    repaint.boundRight = 702;
    if (native_raw_source_only_dirty_crop_can_defer_placement(
            true, 1920u, 1080u, 1920u, 1080u,
            0, 0, 1920, 1080, repaint))
        return false;
    repaint.boundRight = 701;
    after = before;
    delta.capture(before.data(), 8u, after.data(), 8u, 2u, 2u);
    NativeRawSourceIslandBatch unchanged{};
    return !unchanged.append(
        1920u, 1080u, repaint, source, delta, false, true);
}


// The real multi-island Present caller uses the same staged-then-commit
// transaction. A later surface create/lock/copy failure must not publish an
// earlier source RGB island into the original game before fallback.
bool native_raw_two_phase_present_regression() {
    std::array<unsigned, 8> operations{};
    unsigned count = 0u;
    std::uint32_t committed = 99u;
    const bool good = native_raw_preflight_publish_islands(
        3u,
        [&](std::uint32_t i) noexcept { operations[count++] = 10u + i; return true; },
        [&](std::uint32_t i) noexcept { operations[count++] = 20u + i; return true; },
        committed);
    if (!good || committed != 3u || count != 6u ||
        operations[0] != 10u || operations[1] != 11u ||
        operations[2] != 12u || operations[3] != 20u ||
        operations[4] != 21u || operations[5] != 22u)
        return false;
    count = 0u; committed = 99u;
    const bool rejected = native_raw_preflight_publish_islands(
        3u,
        [&](std::uint32_t i) noexcept {
            operations[count++] = 10u + i;
            return i != 2u; // Third D3D9 SYSTEMMEM LockRect failed.
        },
        [&](std::uint32_t i) noexcept {
            operations[count++] = 20u + i; return true;
        },
        committed);
    if (rejected || committed || count != 3u) return false;
    count = 0u; committed = 99u;
    const bool deviceLostDuringCommit = native_raw_preflight_publish_islands(
        3u,
        [&](std::uint32_t i) noexcept {
            operations[count++] = 10u + i; return true;
        },
        [&](std::uint32_t i) noexcept {
            operations[count++] = 20u + i; return i != 1u;
        },
        committed);
    if (deviceLostDuringCommit || committed != 1u || count != 5u)
        return false; // Report partial commit as a failure, never full PASS.
    count = 0u; committed = 99u;
    const bool badCount = native_raw_preflight_publish_islands(
        9u,
        [&](std::uint32_t) noexcept { ++count; return true; },
        [&](std::uint32_t) noexcept { ++count; return true; },
        committed);
    return !badCount && !committed && !count;
}


bool native_raw_packed_island_transfer_regression() {
    constexpr std::uint32_t w = 12u, h = 9u;
    constexpr std::size_t sourcePitch = w * 4u + 8u;
    constexpr std::size_t outputPitch = 3u * 4u + 4u;
    std::array<std::uint8_t, sourcePitch * h> before{}, after{};
    const auto put = [&](std::uint32_t x, std::uint32_t y,
                         std::uint8_t r, std::uint8_t g,
                         std::uint8_t b, std::uint8_t a) {
        auto* p = after.data() + y * sourcePitch + x * 4u;
        p[0] = r; p[1] = g; p[2] = b; p[3] = a;
    };
    put(8u, 5u, 10u, 20u, 30u, 40u);
    put(9u, 6u, 0u, 0u, 0u, 71u); // Alpha-only: no RGB proof.
    const NativeRawPresentTile island{7u, 5u, 3u, 2u, 900, 700};
    if (!native_raw_packed_surface_dimensions_match(3u, 2u, island) ||
        native_raw_packed_surface_dimensions_match(w, h, island) ||
        native_raw_packed_surface_dimensions_match(3u, 1u, island))
        return false; // Recreate a cached surface on menu/car size changes.
    std::array<std::uint8_t, outputPitch * 2u> output{};
    output.fill(0x5au);
    if (!native_raw_copy_packed_present_island(
            output.data(), outputPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, island,
            NativeRawColorByteOrder::Rgba, false))
        return false;
    const auto pixel = [&](std::uint32_t x, std::uint32_t y) {
        return output.data() + y * outputPitch + x * 4u;
    };
    // Source (8,5) maps to packed (1,0), NOT (8,5); the original D3D9
    // destination remains (901,700) via UpdateSurface destination POINT.
    if (pixel(1u, 0u)[0] != 30u ||
        pixel(1u, 0u)[1] != 20u ||
        pixel(1u, 0u)[2] != 10u ||
        pixel(1u, 0u)[3] != 40u ||
        pixel(0u, 0u)[0] != 255u ||
        pixel(0u, 0u)[1] != 0u ||
        pixel(0u, 0u)[2] != 255u ||
        pixel(2u, 1u)[3] != 71u ||
        output[outputPitch - 1u] != 0x5au ||
        output[outputPitch * 2u - 1u] != 0x5au)
        return false;
    // One-pixel native RGB on a real dirty game Present: no resampling,
    // no extraneous rows, and the XRGB alpha is always opaque.
    put(2u, 1u, 51u, 52u, 53u, 54u);
    const NativeRawPresentTile one{2u, 1u, 1u, 1u, 400, 300};
    std::array<std::uint8_t, 8u> tiny{};
    tiny.fill(0x5au);
    if (!native_raw_copy_packed_present_island(
            tiny.data(), 8u, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, one,
            NativeRawColorByteOrder::Bgra, true) ||
        tiny[0] != 51u || tiny[1] != 52u ||
        tiny[2] != 53u || tiny[3] != 255u ||
        tiny[4] != 0x5au)
        return false;
    // Preflight rejects every malformed source/destination extent before
    // writing a single byte, including narrow packed D3D9 lock pitches.
    const auto saved = output;
    NativeRawPresentTile outside = island;
    outside.copyWidth = 6u;
    if (native_raw_copy_packed_present_island(
            output.data(), outputPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, outside,
            NativeRawColorByteOrder::Rgba, false) ||
        native_raw_copy_packed_present_island(
            output.data(), 8u, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, island,
            NativeRawColorByteOrder::Rgba, false) ||
        native_raw_copy_packed_present_island(
            output.data(), outputPitch, before.data(), 12u,
            after.data(), sourcePitch, w, h, island,
            NativeRawColorByteOrder::Rgba, false) ||
        native_raw_copy_packed_present_island(
            output.data(), outputPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, NativeRawPresentTile{},
            NativeRawColorByteOrder::Rgba, false))
        return false;
    return output == saved;
}


 // One authentic source Present may contain more than four separated menu,
 // car or HUD RGB islands. Prove that all eight have distinct original-screen
 // destinations and independent staged publication, not merely a larger enum.
 bool native_raw_eight_island_present_regression() {
     constexpr std::uint32_t w = 16u, h = 8u;
     constexpr std::size_t pitch = w * 4u;
     std::array<std::uint8_t, pitch * h> before{}, first{}, second{};
     for (std::uint32_t n = 0u; n < 4u; ++n) {
         first[(1u * w + 1u + 2u * n) * 4u] =
             static_cast<std::uint8_t>(20u + n);
         second[(3u * w + 9u + 2u * n) * 4u + 1u] =
             static_cast<std::uint8_t>(40u + n);
     }
     NativeRawChangedPixelWindow firstRgb{}, secondRgb{};
     firstRgb.capture(before.data(), pitch, first.data(), pitch, w, h);
     secondRgb.capture(before.data(), pitch, second.data(), pitch, w, h);
     NativeRawPresentDirtyRegion dirty{};
     dirty.headerVerified = true;
     dirty.count = 1u;
     dirty.boundLeft = 100; dirty.boundTop = 300;
     dirty.boundRight = 116; dirty.boundBottom = 308;
     dirty.rectangles[0] = {100, 300, 116, 308};
     const NativeRawPresentTile original{0u, 0u, w, h, 100, 300};
     NativeRawSourceIslandBatch batch{};
     for (std::uint32_t n = 0u; n < 4u; ++n) {
         if (!batch.append(200u, 400u, dirty, original, firstRgb, false, true) ||
             !batch.append(200u, 400u, dirty, original, secondRgb, true, true))
             return false;
         // RGB proof determines which island is selected; candidate
         // subtraction can rank equally sized islands in any safe order.
         // Enforce every original pixel exactly once, not traversal order.
         const auto& a = batch.tiles[n * 2u];
         const auto& b = batch.tiles[n * 2u + 1u];
         if (a.destinationY != 301 || b.destinationY != 303 ||
             a.copyWidth != 1u || a.copyHeight != 1u ||
             b.copyWidth != 1u || b.copyHeight != 1u ||
             batch.rgbPixels[n * 2u] != 1u ||
             batch.rgbPixels[n * 2u + 1u] != 1u ||
             batch.alternate[n * 2u] || !batch.alternate[n * 2u + 1u])
             return false;
         for (std::uint32_t j = 0u; j <= n; ++j) {
             const auto& priorA = batch.tiles[2u * j];
             const auto& priorB = batch.tiles[2u * j + 1u];
             if (priorA.destinationX < 101 || priorA.destinationX > 107 ||
                 ((priorA.destinationX - 101) % 2) != 0 ||
                 priorB.destinationX < 109 || priorB.destinationX > 115 ||
                 ((priorB.destinationX - 109) % 2) != 0)
                 return false;
             if (j != n &&
                 (a.destinationX == priorA.destinationX ||
                  b.destinationX == priorB.destinationX))
                 return false;
         }
     }
     if (batch.count != NativeRawSourceIslandBatch::kMaxIslands ||
         batch.append(200u, 400u, dirty, original, firstRgb, false, true))
         return false;
     std::uint32_t staged = 0u, published = 0u, committed = 99u;
     if (!native_raw_preflight_publish_islands(
             batch.count,
             [&](std::uint32_t i) {
                 ++staged;
                 return i < batch.count &&
                     batch.tiles[i].copyWidth == 1u;
             },
             [&](std::uint32_t i) {
                 ++published;
                 return i < batch.count;
             }, committed) ||
         staged != 8u || published != 8u || committed != 8u)
         return false;
     staged = published = 0u; committed = 99u;
     // Even the eighth LockRect failure must keep ALL seven valid earlier
     // staged islands off the original game's D3D9 backbuffer.
     if (native_raw_preflight_publish_islands(
             batch.count,
             [&](std::uint32_t i) {
                 ++staged;
                 return i != 7u;
             },
             [&](std::uint32_t) {
                 ++published;
                 return true;
             }, committed) ||
         staged != 8u || published != 0u || committed != 0u)
         return false;
     return true;
 }

// Reserve a scarce source-authenticated Present budget for the most real
// D3D11 RGB. Round-robin once published four 1px fragments from the alternate
// capture ahead of four 2x2 menu panels from the primary capture. The full
// eight-slot integrated path must paint all 32 authentic primary pixels.
// When only two primary panels remain, it must also admit six distinct
// alternate pixels; none may overlap or leave its game source coordinates.
bool native_raw_ranked_two_capture_present_regression() {
    constexpr std::uint32_t width = 32u, height = 12u;
    constexpr std::size_t pitch = width * 4u;
    std::array<std::uint8_t, pitch * height> baseline{}, primary{}, secondary{};
    for (std::uint32_t n = 0u; n < 8u; ++n) {
        const std::uint32_t x = 1u + 4u * n;
        for (std::uint32_t y = 1u; y < 3u; ++y)
            for (std::uint32_t xx = x; xx < x + 2u; ++xx)
                primary[(y * width + xx) * 4u] =
                    static_cast<std::uint8_t>(40u + n);
        secondary[(8u * width + x) * 4u + 1u] =
            static_cast<std::uint8_t>(100u + n);
    }
    NativeRawChangedPixelWindow first{}, second{};
    first.capture(baseline.data(), pitch, primary.data(), pitch, width, height);
    second.capture(baseline.data(), pitch, secondary.data(), pitch, width, height);
    NativeRawPresentDirtyRegion dirty{};
    dirty.headerVerified = true; dirty.count = 1u;
    dirty.boundLeft = 100; dirty.boundTop = 300;
    dirty.boundRight = 132; dirty.boundBottom = 312;
    dirty.rectangles[0] = {100, 300, 132, 312};
    const NativeRawPresentTile source{0u, 0u, width, height, 100, 300};
    NativeRawSourceIslandBatch batch{};
    for (std::uint32_t i = 0u; i < 8u; ++i)
        if (!batch.append_best_of_two(
                320u, 480u, dirty, &source, &first, &source, &second))
            return false;
    if (batch.count != 8u) return false;
    std::uint32_t totalRgb = 0u;
    for (std::uint32_t i = 0u; i < batch.count; ++i) {
        const auto& tile = batch.tiles[i];
        if (batch.alternate[i] || batch.rgbPixels[i] != 4u ||
            tile.copyWidth != 2u || tile.copyHeight != 2u ||
            tile.destinationY != 301 ||
            tile.destinationX < 101 || tile.destinationX > 129 ||
            ((tile.destinationX - 101) % 4) != 0)
            return false;
        totalRgb += batch.rgbPixels[i];
        for (std::uint32_t j = 0u; j < i; ++j)
            if (!native_raw_disjoint_present_tiles(tile, batch.tiles[j]))
                return false;
    }
    if (totalRgb != 32u || batch.append_best_of_two(
            320u, 480u, dirty, &source, &first, &source, &second))
        return false;
    // Two high-evidence panels and six genuinely separate alternate pixels
    // must survive an actual two-source priority switch in the same batch.
    for (std::uint32_t n = 2u; n < 8u; ++n)
        for (std::uint32_t y = 1u; y < 3u; ++y)
            for (std::uint32_t x = 1u + 4u * n; x < 3u + 4u * n; ++x)
                primary[(y * width + x) * 4u] = 0u;
    first.capture(baseline.data(), pitch, primary.data(), pitch, width, height);
    NativeRawSourceIslandBatch mixed{};
    for (std::uint32_t i = 0u; i < 8u; ++i)
        if (!mixed.append_best_of_two(
                320u, 480u, dirty, &source, &first, &source, &second))
            return false;
    std::uint32_t firstCount = 0u, secondCount = 0u;
    for (std::uint32_t i = 0u; i < mixed.count; ++i) {
        if (mixed.alternate[i]) {
            if (mixed.rgbPixels[i] != 1u ||
                mixed.tiles[i].destinationY != 308) return false;
            ++secondCount;
        } else {
            if (mixed.rgbPixels[i] != 4u ||
                mixed.tiles[i].destinationY != 301) return false;
            ++firstCount;
        }
        for (std::uint32_t j = 0u; j < i; ++j)
            if (!native_raw_disjoint_present_tiles(
                    mixed.tiles[i], mixed.tiles[j])) return false;
    }
    if (firstCount != 2u || secondCount != 6u) return false;
    const auto saved = mixed;
    dirty.boundRight = 133; // forged original D3D9 rcBound
    if (mixed.append_best_of_two(
            320u, 480u, dirty, &source, &first, &source, &second) ||
        mixed.count != saved.count)
        return false;
    return true;
}


 // Authentic GPU RGB spans three D3D9 menu repaint strips while a fourth
 // dirty member extends into a lower decorative arm. The full dirty bound
 // is NOT solid, but the GPU-created core is and stays at true game coords.
 // A detached/forged dirty rectangle must never grant native publication.
 bool native_raw_gpu_core_across_dirty_strips_regression() {
     constexpr std::uint32_t w = 12u, h = 8u;
     constexpr std::size_t pitch = w * 4u;
     std::array<std::uint8_t, pitch * h> pre{}, post{};
     for (std::uint32_t y = 1u; y < 3u; ++y)
         for (std::uint32_t x = 1u; x < 11u; ++x)
             post[(y * w + x) * 4u + 1u] = 0x78u;
     static NativeRawChangedPixelWindow rgb{};
     rgb.capture(pre.data(), pitch, post.data(), pitch, w, h);
     NativeRawPresentDirtyRegion dirty{};
     dirty.headerVerified = true; dirty.count = 4u;
     dirty.rectangles[0] = {100, 200, 104, 203};
     dirty.rectangles[1] = {104, 200, 108, 203};
     dirty.rectangles[2] = {108, 200, 112, 203};
     dirty.rectangles[3] = {104, 203, 108, 208};
     dirty.boundLeft = 100; dirty.boundTop = 200;
     dirty.boundRight = 112; dirty.boundBottom = 208;
     const NativeRawPresentTile origin{0u, 0u, w, h, 100, 200};
     NativeRawSourceIslandBatch batch{};
     if (!batch.append(320u, 240u, dirty, origin, rgb, false, true) ||
         batch.count != 1u || batch.rgbPixels[0] != 20u ||
         batch.tiles[0].sourceX != 1u || batch.tiles[0].sourceY != 1u ||
         batch.tiles[0].destinationX != 101 ||
         batch.tiles[0].destinationY != 201 ||
         batch.tiles[0].copyWidth != 10u ||
         batch.tiles[0].copyHeight != 2u ||
         !native_raw_dirty_region_covers_tile(
             320u, 240u, dirty, batch.tiles[0]))
         return false;
     if (batch.append(320u, 240u, dirty, origin, rgb, true, true))
         return false; // same GPU RGB cannot be published a second time
     dirty.boundRight = 113; // forged D3D9 rcBound must not help
     NativeRawSourceIslandBatch forged{};
     if (forged.append(320u, 240u, dirty, origin, rgb, false, true))
         return false;
     // A 1px gap in the middle strip excludes the entire 10x2 rectangle.
     dirty.boundRight = 112;
     dirty.rectangles[1] = {105, 200, 108, 203};
     NativeRawSourceIslandBatch hole{};
     if (hole.append(320u, 240u, dirty, origin, rgb, false, true) &&
         (!native_raw_dirty_region_covers_tile(
              320u, 240u, dirty, hole.tiles[0]) ||
          hole.rgbPixels[0] != std::uint64_t{hole.tiles[0].copyWidth} *
                                 hole.tiles[0].copyHeight))
         return false;
     return true;
 }


 // Two authentic D3D11 Draws change different parts of a fragmented
 // vehicle/menu repaint. Original D3D9 RGNDATA contains a true 4x4 central
 // HOLE: its rcBound would falsely authorize 144 pixels. The source-owned
 // GPU images contain exactly 128 painted pixels outside that hole.
 bool native_raw_masked_repaint_two_draws_regression() {
     constexpr std::uint32_t w = 12u, h = 12u;
     constexpr std::size_t pitch = w * 4u;
     std::array<std::uint8_t, pitch * h> before{}, first{}, second{};
     NativeRawPresentDirtyRegion dirty{};
     dirty.headerVerified = true;
     dirty.boundLeft = 100; dirty.boundTop = 200;
     dirty.boundRight = 112; dirty.boundBottom = 212;
     for (std::uint32_t cy = 0; cy < 3u; ++cy)
         for (std::uint32_t cx = 0; cx < 3u; ++cx) {
             if (cx == 1u && cy == 1u) continue;
             dirty.rectangles[dirty.count++] = {
                 100 + 4 * cx, 200 + 4 * cy,
                 104 + 4 * cx, 204 + 4 * cy};
         }
     for (std::uint32_t y = 0; y < h; ++y)
         for (std::uint32_t x = 0; x < w; ++x) {
             if (x >= 4u && x < 8u && y >= 4u && y < 8u)
                 continue;
             if (y < 4u || y >= 8u)
                 first[(y * w + x) * 4u + 1u] = 0x5au;
             else
                 second[(y * w + x) * 4u + 2u] = 0x73u;
         }
     NativeRawChangedPixelWindow a{}, b{};
     a.capture(before.data(), pitch, first.data(), pitch, w, h);
     b.capture(before.data(), pitch, second.data(), pitch, w, h);
     const NativeRawPresentTile source{0u, 0u, w, h, 100, 200};
     NativeRawSourceIslandBatch batch{};
     std::uint32_t total = 0u, fromSecond = 0u;
     for (std::uint32_t n = 0; n < 4u; ++n) {
         if (!batch.append_best_of_two(
                 320u, 240u, dirty, &source, &a, &source, &b))
             return false;
         const auto& tile = batch.tiles[n];
         const auto rgb = batch.rgbPixels[n];
         if (!native_raw_dirty_region_covers_tile(
                 320u, 240u, dirty, tile) ||
             rgb != std::uint64_t{tile.copyWidth} * tile.copyHeight ||
             (batch.alternate[n] ? b.changed_pixels(tile) : a.changed_pixels(tile))
                 != rgb) return false;
         for (std::uint32_t i = 0u; i < n; ++i)
             if (!native_raw_disjoint_present_tiles(tile, batch.tiles[i]))
                 return false;
         fromSecond += batch.alternate[n] ? rgb : 0u;
         total += rgb;
     }
     if (total != 128u || fromSecond != 32u || batch.count != 4u ||
         batch.append_best_of_two(
             320u, 240u, dirty, &source, &a, &source, &b))
         return false;
     // A real-game unpainted hole stays unpainted even when the GPU changed
     // source RGB there; original RGNDATA remains the publication authority.
     first[((5u * w) + 5u) * 4u + 1u] = 0xfdu;
     a.capture(before.data(), pitch, first.data(), pitch, w, h);
     NativeRawSourceIslandBatch hole{};
     for (std::uint32_t n = 0u; n < 4u; ++n)
         if (!hole.append_best_of_two(
                 320u, 240u, dirty, &source, &a, &source, &b))
             return false;
     if (hole.append_best_of_two(
             320u, 240u, dirty, &source, &a, &source, &b))
         return false;
     dirty.boundRight = 113; // rcBound forged to include a nonpainted pixel
     NativeRawSourceIslandBatch forged{};
     if (forged.append_best_of_two(
             320u, 240u, dirty, &source, &a, &source, &b))
         return false;
     return true;
 }



 // Larger original-game native capture covers a real menu/car RGB panel
 // beyond the old 256x144 D3D11 staging extent. Screen coordinates, D3D9
 // repaint members, and final GPU byte transport must still be exact.
 bool native_raw_expanded_source_window_regression() {
     constexpr auto w = NativeRawChangedPixelWindow::kWidth;
     constexpr auto h = NativeRawChangedPixelWindow::kHeight;
     static_assert(w == 512u && h == 288u);
     constexpr auto pitch = std::size_t{w} * 4u;
     static std::array<std::uint8_t, pitch * h> pre{}, post{};
     for (std::uint32_t y = 264u; y < 272u; ++y)
         for (std::uint32_t x = 456u; x < 472u; ++x)
             post[(std::size_t{y} * w + x) * 4u + 1u] = 171u;
     static NativeRawChangedPixelWindow gpu{};
     gpu.capture(pre.data(), pitch, post.data(), pitch, w, h);
     NativeRawPresentTile source{};
     if (!native_raw_source_capture_clip_tile(
             1000u, 500u, w, h, 1920u, 1080u,
             1920u, 1080u, 0, 0, 1920, 1080, source) ||
         source.copyWidth != w || source.copyHeight != h)
         return false;
     NativeRawPresentDirtyRegion dirty{};
     dirty.headerVerified = true; dirty.count = 2u;
     dirty.boundLeft = 1456; dirty.boundTop = 764;
     dirty.boundRight = 1472; dirty.boundBottom = 772;
     dirty.rectangles[0] = {1456, 764, 1464, 772};
     dirty.rectangles[1] = {1464, 764, 1472, 772};
     NativeRawSourceIslandBatch batch{};
     if (!batch.append(1920u, 1080u, dirty, source, gpu,
                       false, true) ||
         batch.count != 1u || batch.rgbPixels[0] != 128u ||
         batch.tiles[0].sourceX != 456u ||
         batch.tiles[0].sourceY != 264u ||
         batch.tiles[0].destinationX != 1456 ||
         batch.tiles[0].destinationY != 764 ||
         batch.tiles[0].copyWidth != 16u ||
         batch.tiles[0].copyHeight != 8u ||
         !native_raw_dirty_region_covers_tile(
             1920u, 1080u, dirty, batch.tiles[0]))
         return false;
     std::array<std::uint8_t, 16u * 8u * 4u> packed{};
     if (!native_raw_copy_packed_present_island(
             packed.data(), 16u * 4u,
             pre.data(), pitch, post.data(), pitch, w, h,
             batch.tiles[0], NativeRawColorByteOrder::Bgra, false))
         return false;
     for (std::uint32_t y = 0u; y < 8u; ++y)
         for (std::uint32_t x = 0u; x < 16u; ++x)
             if (packed[(y * 16u + x) * 4u + 1u] != 171u)
                 return false;
     // A duplicate GPU Draw cannot claim an already uploaded D3D9 pixel.
     if (batch.append(1920u, 1080u, dirty, source, gpu, true, true))
         return false;
     // Malformed original dirty bounds never grant RAW publication.
     dirty.boundRight = 1473;
     NativeRawSourceIslandBatch forged{};
     if (forged.append(1920u, 1080u, dirty, source, gpu, false, true))
         return false;
     // A real dirty-region hole can select a smaller authentic island,
     // but cannot publish through the hole.
     dirty.boundRight = 1472;
     dirty.rectangles[1].left = 1465;
     NativeRawSourceIslandBatch hole{};
     if (hole.append(1920u, 1080u, dirty, source, gpu, false, true) &&
         !native_raw_dirty_region_covers_tile(
             1920u, 1080u, dirty, hole.tiles[0]))
         return false;
     return true;
 }

int main() { assert(native_raw_expanded_source_window_regression()); assert(native_raw_changed_crop_regression()); assert(native_raw_tiny_rgb_source_upload_regression()); assert(native_raw_large_crop_sparse_dirty_source_regression()); assert(native_raw_two_phase_present_regression()); assert(native_raw_packed_island_transfer_regression()); assert(native_raw_eight_island_present_regression()); assert(native_raw_ranked_two_capture_present_regression()); assert(native_raw_gpu_core_across_dirty_strips_regression()); assert(native_raw_masked_repaint_two_draws_regression()); }
