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


// Real RGNDATA often splits a repaint into three or more thin strips.
// The native RAW diagnostic must find a TRUE painted component even with
// unrelated dirty islands, but never cross a one-pixel unpainted seam.
// This is source-to-native GPU visibility only, not full-frame promotion.
constexpr bool kRawConnectedDirtyRepaintProof = []() constexpr {
    using namespace outrun::vr::dx11;
    NativeRawPresentDirtyRegion dirty{};
    dirty.headerVerified = true;
    dirty.count = 3u;
    dirty.boundLeft = 600; dirty.boundTop = 300;
    dirty.boundRight = 648; dirty.boundBottom = 348;
    dirty.rectangles[0] = {600, 300, 616, 348};
    dirty.rectangles[1] = {616, 300, 632, 348};
    dirty.rectangles[2] = {632, 300, 648, 348};
    NativeRawPresentTile tile{};
    const auto place = [&]() constexpr {
        return native_raw_dirty_region_place_tile(
            1920, 1080, 0, 0, 1920, 1080,
            dirty, 256, 144, tile);
    };
    if (!place() || tile.copyWidth != 32u ||
        tile.copyHeight != 32u ||
        tile.destinationX != 608 || tile.destinationY != 308 ||
        !native_raw_dirty_region_covers_tile(1920, 1080, dirty, tile))
        return false;
    // A real unpainted 1px source seam cannot become a native tile.
    dirty.rectangles[1] = {617, 300, 632, 348};
    if (place()) return false;
    dirty.rectangles[1] = {616, 300, 632, 348};
    // Fragmented islands plus a distant dirty outlier: all 21 members
    // are authenticated; the connected 20-strip component still paints
    // a 24x32 crop without expanding the D3D9 Present source.
    dirty.count = 21u;
    for (std::uint32_t i = 0u; i < 20u; ++i) {
        const auto x = static_cast<std::int64_t>(600 + 2 * i);
        dirty.rectangles[i] = {x, 300, x + 2, 348};
    }
    dirty.rectangles[20] = {1500, 700, 1516, 716};
    dirty.boundRight = 1516; dirty.boundBottom = 716;
    if (!place() || tile.copyWidth != 24u ||
        tile.copyHeight != 32u || tile.destinationX != 608 ||
        tile.destinationY != 308 ||
        !native_raw_dirty_region_covers_tile(1920, 1080, dirty, tile))
        return false;
    // Even one missing strip breaks component coverage; an isolated
    // sub-40px remainder cannot individually authorize a RAW crop.
    dirty.rectangles[10] = {621, 300, 622, 348};
    if (place()) return false;
    dirty.rectangles[10] = {620, 300, 622, 348};
    // A malformed outlier invalidates the entire claimed RGNDATA union.
    dirty.rectangles[20] = {1500, 700, 2000, 716};
    if (place()) return false;
    dirty.rectangles[20] = {1500, 700, 1516, 716};
    dirty.boundRight = 1517; // forged rcBound
    if (place()) return false;
    dirty.boundRight = 1516;
    dirty.headerVerified = false;
    if (place()) return false;
    return true;
}();
static_assert(kRawConnectedDirtyRepaintProof,
              "fragmented source repaint cannot fabricate native GPU pixels");

// Distinct authentic D3D9 dirty islands must be able to display both
// independent source Draw GPU captures, not an imaginary contiguous frame.
constexpr bool kRawDisjointRepaintPairProof = []() constexpr {
    using namespace outrun::vr::dx11;
    NativeRawPresentDirtyRegion dirty{};
    dirty.headerVerified = true;
    dirty.count = 2u;
    dirty.rectangles[0] = {600, 300, 648, 348};
    dirty.rectangles[1] = {900, 300, 948, 348};
    dirty.boundLeft = 600; dirty.boundTop = 300;
    dirty.boundRight = 948; dirty.boundBottom = 348;
    const NativeRawPresentTile first{0u, 0u, 32u, 32u, 608, 308};
    NativeRawPresentTile second{};
    const auto findSecond = [&]() constexpr {
        return native_raw_dirty_region_place_tile(
            1920, 1080, 0, 0, 1920, 1080,
            dirty, 32, 32, second, &first);
    };
    if (!native_raw_dirty_region_covers_tile(1920, 1080, dirty, first) ||
        !findSecond() || second.destinationX != 908 ||
        second.destinationY != 308 ||
        !native_raw_disjoint_equal_tiles(first, second) ||
        !native_raw_dirty_region_covers_tile(1920, 1080, dirty, second))
        return false;
    const NativeRawPresentTile unpainted{0u, 0u, 32u, 32u, 568, 308};
    if (native_raw_dirty_region_covers_tile(1920, 1080, dirty, unpainted))
        return false;
    // No second island large enough to hold the same genuine GPU window.
    dirty.rectangles[1] = {900, 300, 923, 348};
    dirty.boundRight = 923;
    if (findSecond()) return false;
    dirty.rectangles[1] = {900, 300, 948, 348};
    dirty.boundRight = 949; // source rcBound forgery
    if (findSecond()) return false;
    dirty.boundRight = 948;
    dirty.rectangles[1].right = 2000; // invalid member
    if (findSecond()) return false;
    dirty.rectangles[1].right = 948;
    dirty.headerVerified = false;
    if (findSecond()) return false;
    dirty.headerVerified = true;
    // Present source crop exposes only first island; never paint a second.
    if (native_raw_dirty_region_place_tile(
            1920, 1080, 580, 280, 660, 360,
            dirty, 32, 32, second, &first)) return false;
    // A guessed first tile cannot reserve or authorize pixels.
    const NativeRawPresentTile forgedFirst{0u, 0u, 32u, 32u, 400, 308};
    if (native_raw_dirty_region_place_tile(
            1920, 1080, 0, 0, 1920, 1080,
            dirty, 32, 32, second, &forgedFirst)) return false;
    return true;
}();
static_assert(kRawDisjointRepaintPairProof,
    "RAW paired GPU pixels need two genuine nonoverlapping dirty islands");

// Three narrow pieces form a real 48x48 repaint, but an attached thin tail
// makes the connected component's top-right candidate unpainted.
constexpr bool kRawTailedRepaintProof = []() constexpr {
    using namespace outrun::vr::dx11;
    NativeRawPresentDirtyRegion dirty{};
    dirty.headerVerified = true;
    dirty.count = 4u;
    dirty.boundLeft = 600; dirty.boundTop = 300;
    dirty.boundRight = 900; dirty.boundBottom = 348;
    dirty.rectangles[0] = {600, 300, 616, 348};
    dirty.rectangles[1] = {616, 300, 632, 348};
    dirty.rectangles[2] = {632, 300, 648, 348};
    dirty.rectangles[3] = {648, 300, 900, 308};
    NativeRawPresentTile tile{};
    const auto place = [&]() constexpr {
        return native_raw_dirty_region_place_tile(
            1920, 1080, 0, 0, 1920, 1080, dirty, 256, 144, tile);
    };
    if (!place() || tile.copyWidth != 32u || tile.copyHeight != 32u ||
        tile.destinationX != 608 || tile.destinationY != 308 ||
        !native_raw_dirty_region_covers_tile(1920, 1080, dirty, tile))
        return false;
    // The source crop may clip the tail without changing the painted island.
    if (!native_raw_dirty_region_place_tile(
            1920, 1080, 590, 290, 850, 360, dirty, 256, 144, tile))
        return false;
    dirty.rectangles[1].left = 617; // authentic one-pixel hole
    if (place()) return false;
    dirty.rectangles[1].left = 616;
    dirty.boundRight = 901; // no fabricated rcBound
    if (place()) return false;
    dirty.boundRight = 900;
    dirty.rectangles[3].right = 2000; // invalid tail invalidates ALL output
    if (place()) return false;
    return true;
}();
static_assert(kRawTailedRepaintProof,
    "connected thin tails must not hide authentic native GPU repaint islands");

