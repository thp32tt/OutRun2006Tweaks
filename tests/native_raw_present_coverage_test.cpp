// Genuine full/cropped native GPU tile output is not lost just because
// D3D9 supplied an explicit, verified dirty region for the same source crop.
#include "../src/vr/d3d11/native_game_raw_present_coverage.hpp"
#include <cassert>
using outrun::vr::dx11::native_raw_preview_present_coverage;
constexpr bool kSafeRawPresentCoverage =
    native_raw_preview_present_coverage(false, false, false, false) &&
    native_raw_preview_present_coverage(true, true, false, false) &&
    native_raw_preview_present_coverage(true, false, true, false) &&
    native_raw_preview_present_coverage(true, false, false, true) &&
    !native_raw_preview_present_coverage(true, false, false, false) &&
    !native_raw_preview_present_coverage(true, false, false, false);
static_assert(kSafeRawPresentCoverage,
              "unproven D3D9 dirty source crops must not publish RAW tiles");
int main() { assert(kSafeRawPresentCoverage); }

// Partial source-dirty Presents may still visibly display an authenticated
// opt-in RAW GPU region; neither rcBound alone nor a partial intersecting
// region can certify changed pixels as actually presented.
constexpr bool kRawDirtyTileProof = []() constexpr {
    using namespace outrun::vr::dx11;
    NativeRawPresentTile first{0u, 0u, 120u, 80u, 600, 20};
    NativeRawPresentTile second{0u, 0u, 120u, 80u, 450, 20};
    NativeRawPresentDirtyRegion dirty{};
    dirty.headerVerified = true;
    dirty.count = 1u;
    dirty.rectangles[0] = {600, 20, 720, 100};
    dirty.boundLeft = 600; dirty.boundTop = 20;
    dirty.boundRight = 720; dirty.boundBottom = 100;
    if (!native_raw_dirty_region_covers_tile(800, 450, dirty, first) ||
        native_raw_dirty_region_covers_tile(800, 450, dirty, second))
        return false;
    // Two adjacent dirty rectangles really do cover the whole selected tile,
    // despite neither rectangle independently covering it.
    dirty.count = 2u;
    dirty.rectangles[0] = {600, 20, 660, 100};
    dirty.rectangles[1] = {660, 20, 720, 100};
    if (!native_raw_dirty_region_covers_tile(800, 450, dirty, first))
        return false;
    dirty.rectangles[1] = {661, 20, 720, 100}; // one-pixel hole
    if (native_raw_dirty_region_covers_tile(800, 450, dirty, first))
        return false;
    dirty.rectangles[1] = {660, 20, 720, 100};
    dirty.boundRight = 800; // forged rcBound
    if (native_raw_dirty_region_covers_tile(800, 450, dirty, first))
        return false;
    dirty.boundRight = 720;
    dirty.rectangles[1] = {660, 20, 900, 100}; // out of backbuffer
    if (native_raw_dirty_region_covers_tile(800, 450, dirty, first))
        return false;
    dirty.rectangles[1] = {660, 20, 720, 100};
    dirty.count = 33u; // refuse unbounded RGNDATA payload
    if (native_raw_dirty_region_covers_tile(800, 450, dirty, first))
        return false;
    dirty.count = 2u;
    dirty.headerVerified = false;
    if (native_raw_dirty_region_covers_tile(800, 450, dirty, first))
        return false;
    // Partial dirty coverage is never a replacement for FULL-frame proof.
    if (native_raw_preview_present_coverage(true, false, false, false))
        return false;
    return true;
}();
static_assert(kRawDirtyTileProof, "RAW dirty-region tile proof must fail closed");
