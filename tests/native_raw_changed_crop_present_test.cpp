// Authentic pre/post native Draw pixels must remain visible in even the
// smallest supported D3D9 source Present crop. No full-frame promotion.
#include "../src/vr/d3d11/native_game_raw_partial_present_tile.hpp"
#include "../src/vr/d3d11/native_game_raw_color_transport.hpp"
#include "../src/vr/d3d11/native_game_raw_present_coverage.hpp"
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
    NativeRawChangedPixelWindow gpu{};
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

int main() { assert(native_raw_changed_crop_regression()); assert(native_raw_tiny_rgb_source_upload_regression()); }
