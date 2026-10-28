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

 // Partial dirty menu/car Present: a real 48x48 repaint cannot show the
 // usual 256x144 top-right tile, but safely admits a 32x32 RAW GPU crop.
 constexpr bool kRawDirtyPlacementProof = []() constexpr {
     using namespace outrun::vr::dx11;
     NativeRawPresentDirtyRegion dirty{};
     dirty.headerVerified = true;
     dirty.count = 1u;
     dirty.rectangles[0] = {600, 300, 648, 348};
     dirty.boundLeft = 600; dirty.boundTop = 300;
     dirty.boundRight = 648; dirty.boundBottom = 348;
     NativeRawPresentTile placed{};
     if (!native_raw_dirty_region_place_tile(
             1920, 1080, 0, 0, 1920, 1080, dirty,
             256, 144, placed) ||
         placed.copyWidth != 32u || placed.copyHeight != 32u ||
         placed.destinationX != 608 || placed.destinationY != 308 ||
         !native_raw_dirty_region_covers_tile(1920, 1080, dirty, placed))
         return false;
     // Two partial regions: pick the largest authenticated available crop.
     dirty.count = 2u;
     dirty.rectangles[1] = {700, 350, 780, 410};
     dirty.boundRight = 780; dirty.boundBottom = 410;
     if (!native_raw_dirty_region_place_tile(
             1920, 1080, 0, 0, 1920, 1080, dirty,
             256, 144, placed) ||
         placed.copyWidth != 64u || placed.copyHeight != 44u ||
         placed.destinationX != 708 || placed.destinationY != 358)
         return false;
     // An rcBound forgery, hole, unknown header, out-of-bounds rect, and
     // a repaint too small for the labeled RAW tile must all fail closed.
     dirty.boundRight = 781;
     if (native_raw_dirty_region_place_tile(
             1920, 1080, 0, 0, 1920, 1080, dirty,
             256, 144, placed)) return false;
     dirty.boundRight = 780;
     dirty.rectangles[1] = {700, 350, 2000, 410};
     if (native_raw_dirty_region_place_tile(
             1920, 1080, 0, 0, 1920, 1080, dirty,
             256, 144, placed)) return false;
     dirty.count = 1u;
     dirty.rectangles[0] = {600, 300, 620, 320};
     dirty.boundLeft = 600; dirty.boundTop = 300;
     dirty.boundRight = 620; dirty.boundBottom = 320;
     if (native_raw_dirty_region_place_tile(
             1920, 1080, 0, 0, 1920, 1080, dirty,
             256, 144, placed)) return false;
     dirty.headerVerified = false;
     if (native_raw_dirty_region_place_tile(
             1920, 1080, 0, 0, 1920, 1080, dirty,
             256, 144, placed)) return false;
     return true;
 }();
 static_assert(kRawDirtyPlacementProof,
               "RAW GPU visibility requires actual D3D9 dirty repaint");


// A legitimate D3D9 dirty UNION can show native GPU RGB where every member
// rectangle by itself is too narrow/short. A missing pixel must still block
// the whole RAW diagnostic tile, regardless of a plausible rcBound.
constexpr bool kRawDirtyFragmentUnionProof = []() constexpr {
    using namespace outrun::vr::dx11;
    NativeRawPresentDirtyRegion dirty{};
    dirty.headerVerified = true;
    dirty.count = 2u;
    dirty.boundLeft = 600; dirty.boundTop = 300;
    dirty.boundRight = 648; dirty.boundBottom = 348;
    NativeRawPresentTile tile{};
    // Horizontal split: each 24x48 rect fails the individual minimum.
    dirty.rectangles[0] = {600, 300, 624, 348};
    dirty.rectangles[1] = {624, 300, 648, 348};
    const auto goodTile = [&]() constexpr {
        return native_raw_dirty_region_place_tile(
                   1920, 1080, 0, 0, 1920, 1080,
                   dirty, 256, 144, tile) &&
               tile.copyWidth == 32u && tile.copyHeight == 32u &&
               tile.destinationX == 608 && tile.destinationY == 308 &&
               native_raw_dirty_region_covers_tile(
                   1920, 1080, dirty, tile);
    };
    if (!goodTile()) return false;
    // Vertical split and exact-edge overlap are equally source-authentic.
    dirty.rectangles[0] = {600, 300, 648, 324};
    dirty.rectangles[1] = {600, 324, 648, 348};
    if (!goodTile()) return false;
    // Gap in the horizontal union cannot be treated as painted pixels.
    dirty.rectangles[0] = {600, 300, 624, 348};
    dirty.rectangles[1] = {625, 300, 648, 348};
    if (native_raw_dirty_region_place_tile(
            1920, 1080, 0, 0, 1920, 1080, dirty,
            256, 144, tile)) return false;
    // Two real adjoining fragments amid an unrelated small repaint:
    // rcBound is too large, but the exact pair union still qualifies.
    dirty.count = 3u;
    dirty.rectangles[1] = {624, 300, 648, 348};
    dirty.rectangles[2] = {1500, 700, 1516, 716};
    dirty.boundRight = 1516; dirty.boundBottom = 716;
    if (!goodTile()) return false;
    // Extra unrelated rectangle must not conceal forged or missing paint.
    dirty.rectangles[1] = {625, 300, 648, 348};
    if (native_raw_dirty_region_place_tile(
            1920, 1080, 0, 0, 1920, 1080, dirty,
            256, 144, tile)) return false;
    dirty.rectangles[1] = {624, 300, 648, 348};
    dirty.rectangles[2] = {1500, 700, 2000, 716};
    if (native_raw_dirty_region_place_tile(
            1920, 1080, 0, 0, 1920, 1080, dirty,
            256, 144, tile)) return false;
    return true;
}();
static_assert(kRawDirtyFragmentUnionProof,
              "RAW tiles require a painted D3D9 dirty union without gaps");
