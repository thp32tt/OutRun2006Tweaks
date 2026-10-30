// Authentic pre/post native Draw pixels must remain visible in even the
// smallest supported D3D9 source Present crop. No full-frame promotion.
#include "../src/vr/d3d11/native_game_raw_partial_present_tile.hpp"
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
    // Previously a 24..39px full native-game repaint was rejected by the
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
        native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 723, 324, 256, 144, small) ||
        native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 740, 340, 256, 144, small) ||
        native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 700, 300, 724, 324, 23, 144, small) ||
        native_raw_verified_small_source_present_tile(
            true, 1920, 1080, 1900, 1060, 1921, 1081, 256, 144, small))
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
int main() { assert(native_raw_changed_crop_regression()); }
