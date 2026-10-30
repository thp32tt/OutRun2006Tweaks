#include "src/vr/d3d11/native_game_raw_dual_tile.hpp"
#include "src/vr/d3d11/native_game_raw_color_transport.hpp"
#include "src/vr/d3d11/native_game_raw_changed_pixel_window.hpp"
#include "src/vr/d3d11/native_game_raw_present_coverage.hpp"
#include "src/vr/d3d11/native_game_raw_source_target_identity.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11;
int main() {
    // Different D3D9 interface pointers may identify the same canonical
    // game backbuffer. Never accept an unrelated or unavailable IUnknown.
    int drawSurface = 0, presentedSurface = 0, canonical = 0, foreign = 0;
    assert(native_raw_canonical_source_target_is_presented(
        &drawSurface, &presentedSurface, &canonical, &canonical));
    assert(!native_raw_canonical_source_target_is_presented(
        &drawSurface, &presentedSurface, &canonical, &foreign));
    assert(!native_raw_canonical_source_target_is_presented(
        &drawSurface, &presentedSurface, &canonical,
        static_cast<int*>(nullptr)));
    assert(!native_raw_canonical_source_target_is_presented(
        static_cast<int*>(nullptr), &presentedSurface,
        &canonical, &canonical));
    // Source-coincident RAW publishing previously rejected the ENTIRE
    // 64x40 tile if the game repainted only a smaller legitimate dirty island.
    // This must preserve exactly the GPU source coordinates and RGB evidence.
    {
        constexpr std::uint32_t w = 96u, h = 64u;
        std::array<std::uint8_t, w * h * 4u> prior{};
        auto after = prior;
        after[(22u * w + 65u) * 4u + 2u] = 201u;
        NativeRawChangedPixelWindow delta;
        delta.capture(prior.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion island{};
        island.headerVerified = true;
        island.count = 1u;
        island.rectangles[0] = {160, 220, 173, 236};
        island.boundLeft = 160; island.boundTop = 220;
        island.boundRight = 173; island.boundBottom = 236;
        const NativeRawPresentTile fullGpuTile{10u, 10u, 64u, 40u, 110, 210};
        NativeRawPresentTile cropped{};
        std::uint32_t realRgb = 0u;
        assert(!native_raw_dirty_region_covers_tile(
            1920, 1080, island, fullGpuTile));
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, island, fullGpuTile, delta, cropped, realRgb));
        assert(realRgb == 1u && cropped.sourceX == 60u &&
               cropped.sourceY == 20u && cropped.copyWidth == 13u &&
               cropped.copyHeight == 16u && cropped.destinationX == 160 &&
               cropped.destinationY == 220);
        assert(delta.changed_pixels(cropped) == realRgb);
        // A second independent native Draw on the SAME original
        // backbuffer can repaint a DIFFERENT-size dirty island. Keep the
        // actual source-pixel coordinates and both GPU RGB contributions.
        NativeRawPresentDirtyRegion twoIslands = island;
        twoIslands.count = 2u;
        twoIslands.rectangles[1] = {356, 220, 374, 246};
        twoIslands.boundRight = 374;
        twoIslands.boundBottom = 246;
        const NativeRawPresentTile secondDraw{5u, 5u, 64u, 40u, 310, 210};
        NativeRawPresentTile secondCrop{};
        std::uint32_t secondRgb = 0u;
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, twoIslands, secondDraw, delta,
            secondCrop, secondRgb));
        assert(secondRgb == 1u && secondCrop.sourceX == 51u &&
               secondCrop.sourceY == 15u && secondCrop.copyWidth == 18u &&
               secondCrop.copyHeight == 26u &&
               secondCrop.destinationX == 356 &&
               secondCrop.destinationY == 220);
        assert(native_raw_dirty_region_covers_tile(
            1920, 1080, twoIslands, cropped));
        assert(native_raw_dirty_region_covers_tile(
            1920, 1080, twoIslands, secondCrop));
        assert(native_raw_can_show_source_aligned_pair(
            false, true, true, cropped, secondCrop));
        // More than two contiguous real game dirty rectangles may cover a
        // single native GPU Draw RGB island. Select their true rectangular
        // union instead of discarding all but one source fragment.
        {
            std::array<std::uint8_t, w * h * 4u> fragmentedBefore{};
            auto fragmentedAfter = fragmentedBefore;
            fragmentedAfter[(22u * w + 65u) * 4u] = 71u;
            fragmentedAfter[(22u * w + 75u) * 4u + 1u] = 83u;
            NativeRawChangedPixelWindow rgbUnion;
            rgbUnion.capture(fragmentedBefore.data(), w * 4u,
                             fragmentedAfter.data(), w * 4u, w, h);
            // Unlike the prior 64px sample, the fragmented full crop must
            // cover the second authentic RGB pixel at source x=75.
            const NativeRawPresentTile fragmentedGpu{10u, 10u, 76u, 40u, 110, 210};
            NativeRawPresentDirtyRegion fragments{};
            fragments.headerVerified = true;
            fragments.count = 3u;
            fragments.rectangles[0] = {160, 220, 166, 236};
            fragments.rectangles[1] = {166, 220, 172, 236};
            fragments.rectangles[2] = {172, 220, 180, 236};
            fragments.boundLeft = 160; fragments.boundTop = 220;
            fragments.boundRight = 180; fragments.boundBottom = 236;
            NativeRawPresentTile multi{};
            std::uint32_t rgbCount = 0u;
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, fragments, fragmentedGpu, rgbUnion,
                multi, rgbCount));
            assert(rgbCount == 2u && multi.sourceX == 60u &&
                   multi.sourceY == 20u && multi.copyWidth == 20u &&
                   multi.copyHeight == 16u && multi.destinationX == 160 &&
                   multi.destinationY == 220);
            assert(native_raw_dirty_region_covers_tile(
                1920, 1080, fragments, multi));
            // Missing ONE real destination pixel breaks the union:
            // never stretch a native GPU fragment across a D3D9 dirty gap.
            fragments.rectangles[2].left = 173;
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, fragments, fragmentedGpu, rgbUnion,
                multi, rgbCount));
            assert(rgbCount == 1u && multi.copyWidth < 20u);
            // Repaint geometry is untrusted until rcBound agrees with
            // every member. Even a real RGB source pixel cannot override it.
            fragments.boundRight = 181;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, fragments, fragmentedGpu, rgbUnion,
                multi, rgbCount));
            // Vertical fragmented game repaint is equally source-coincident.
            fragmentedAfter[(33u * w + 65u) * 4u + 2u] = 93u;
            rgbUnion.capture(fragmentedBefore.data(), w * 4u,
                             fragmentedAfter.data(), w * 4u, w, h);
            fragments = {};
            fragments.headerVerified = true;
            fragments.count = 2u;
            fragments.rectangles[0] = {160, 220, 180, 228};
            fragments.rectangles[1] = {160, 228, 180, 236};
            fragments.boundLeft = 160; fragments.boundTop = 220;
            fragments.boundRight = 180; fragments.boundBottom = 236;
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, fragments, fragmentedGpu, rgbUnion,
                multi, rgbCount));
            assert(rgbCount == 3u && multi.copyWidth == 20u &&
                   multi.copyHeight == 16u && multi.destinationX == 160 &&
                   multi.destinationY == 220);
        }
        // The real DX11 PRE/POST RGB can land at OPPOSITE corners of
        // nine 16x16 D3D9 menu/vehicle repaint cells. A thin attached tail
        // makes the whole connected component bounding box non-rectangular.
        // Neither the per-member nor connected-bounds crop can preserve both.
        {
            std::array<std::uint8_t, w * h * 4u> gridBefore{};
            auto gridAfter = gridBefore;
            // Original backbuffer (130,230) and (170,260), not relocated.
            gridAfter[(20u * w + 20u) * 4u + 0u] = 51u;
            gridAfter[(50u * w + 60u) * 4u + 2u] = 92u;
            NativeRawChangedPixelWindow gridRgb{};
            gridRgb.capture(gridBefore.data(), w * 4u,
                            gridAfter.data(), w * 4u, w, h);
            NativeRawPresentDirtyRegion grid{};
            grid.headerVerified = true;
            grid.count = 10u;
            for (std::uint32_t gy = 0u; gy < 3u; ++gy)
                for (std::uint32_t gx = 0u; gx < 3u; ++gx)
                    grid.rectangles[gy * 3u + gx] = {
                        125 + std::int64_t{gx} * 16,
                        220 + std::int64_t{gy} * 16,
                        141 + std::int64_t{gx} * 16,
                        236 + std::int64_t{gy} * 16};
            grid.rectangles[9] = {173, 220, 185, 232};
            grid.boundLeft = 125; grid.boundTop = 220;
            grid.boundRight = 185; grid.boundBottom = 268;
            const NativeRawPresentTile entireGpu{0u, 0u, w, h, 110, 210};
            NativeRawPresentTile chosen{};
            std::uint32_t rgb = 0u;
            assert(!native_raw_dirty_region_covers_tile(
                1920, 1080, grid, entireGpu));
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, grid, entireGpu, gridRgb, chosen, rgb));
            assert(rgb == 2u && chosen.sourceX == 15u &&
                   chosen.sourceY == 10u && chosen.copyWidth == 48u &&
                   chosen.copyHeight == 48u && chosen.destinationX == 125 &&
                   chosen.destinationY == 220);
            assert(native_raw_dirty_region_covers_tile(
                1920, 1080, grid, chosen));
            assert(gridRgb.changed_pixels(chosen) == 2u);
            // Remove the painted centre: bounding-box and component proofs
            // must not stretch GPU pixels across the missing D3D9 rectangle.
            grid.rectangles[4] = {185, 220, 189, 232};
            grid.boundRight = 189;
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, grid, entireGpu, gridRgb, chosen, rgb));
            assert(rgb == 1u);
            // A forged rcBound invalidates the ENTIRE region, not just the
            // candidate whose box happens to match it.
            grid.boundRight = 190;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, grid, entireGpu, gridRgb, chosen, rgb));
            assert(rgb == 0u);
            // Source alpha cannot masquerade as real GPU-generated RGB.
            grid = {};
            grid.headerVerified = true; grid.count = 1u;
            grid.rectangles[0] = {125, 220, 173, 268};
            grid.boundLeft = 125; grid.boundTop = 220;
            grid.boundRight = 173; grid.boundBottom = 268;
            gridAfter = gridBefore;
            gridAfter[(20u * w + 20u) * 4u + 3u] = 255u;
            gridRgb.capture(gridBefore.data(), w * 4u,
                            gridAfter.data(), w * 4u, w, h);
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, grid, entireGpu, gridRgb, chosen, rgb));
        }
        // One authentic native GPU Draw can change two DISJOINT
        // original D3D9 menu/car dirty islands. The second needs its own
        // UpdateSurface rect, not a widened hole-filling bounding box.
        {
            constexpr std::uint32_t pw = 96u, ph = 64u;
            std::array<std::uint8_t, pw * ph * 4u> beforePair{};
            auto afterPair = beforePair;
            afterPair[(20u * pw + 20u) * 4u] = 31u;
            afterPair[(35u * pw + 70u) * 4u + 2u] = 91u;
            NativeRawChangedPixelWindow pairRgb{};
            pairRgb.capture(beforePair.data(), pw * 4u,
                            afterPair.data(), pw * 4u, pw, ph);
            NativeRawPresentDirtyRegion islands{};
            islands.headerVerified = true;
            islands.count = 2u;
            islands.rectangles[0] = {110, 210, 140, 235};
            islands.rectangles[1] = {160, 225, 180, 255};
            islands.boundLeft = 110; islands.boundTop = 210;
            islands.boundRight = 180; islands.boundBottom = 255;
            const NativeRawPresentTile fullCapture{0u, 0u, pw, ph, 100, 200};
            NativeRawPresentTile primary{}, remainder{};
            std::uint32_t primaryRgb = 0u, remainderRgb = 0u;
            assert(!native_raw_dirty_region_covers_tile(
                1920, 1080, islands, fullCapture));
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                primary, primaryRgb));
            assert(primaryRgb == 1u && primary.destinationX == 110 &&
                   primary.destinationY == 210);
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                remainder, remainderRgb, &primary));
            assert(remainderRgb == 1u && remainder.destinationX == 160 &&
                   remainder.destinationY == 225 &&
                   native_raw_disjoint_present_tiles(primary, remainder));
            assert(pairRgb.changed_pixels(primary) == 1u &&
                   pairRgb.changed_pixels(remainder) == 1u);
            // Repeated passes may not redisplay the same real source pixel.
            NativeRawPresentTile third{};
            std::uint32_t thirdRgb = 99u;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                third, thirdRgb, &fullCapture));
            assert(thirdRgb == 0u);
            // A forged rcBound never permits either GPU upload.
            islands.boundRight = 181;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                third, thirdRgb, &primary));
            assert(thirdRgb == 0u);
            islands.boundRight = 180;
            // Alpha-only output in the second island is not native RGB.
            afterPair[(35u * pw + 70u) * 4u + 2u] = 0u;
            afterPair[(35u * pw + 70u) * 4u + 3u] = 255u;
            pairRgb.capture(beforePair.data(), pw * 4u,
                            afterPair.data(), pw * 4u, pw, ph);
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                remainder, remainderRgb, &primary));
            assert(remainderRgb == 0u);
        }
        // A live GPU Draw can change FOUR disjoint menu/vehicle repaint
        // regions. Each source-aligned UpdateSurface needs an independent
        // immutable staging surface and a non-overlapping exact-source crop.
        {
            constexpr std::uint32_t mw = 128u, mh = 96u;
            std::array<std::uint8_t, mw * mh * 4u> beforeMulti{};
            auto afterMulti = beforeMulti;
            const std::uint32_t xs[4]{16u, 56u, 16u, 106u};
            const std::uint32_t ys[4]{16u, 16u, 61u, 61u};
            NativeRawPresentDirtyRegion four{};
            four.headerVerified = true;
            four.count = 4u;
            for (std::uint32_t i = 0u; i < four.count; ++i) {
                afterMulti[(ys[i] * mw + xs[i]) * 4u + (i % 3u)] =
                    static_cast<std::uint8_t>(50u + i);
                four.rectangles[i] = {200 + std::int64_t{xs[i]} - 6,
                    300 + std::int64_t{ys[i]} - 6,
                    200 + std::int64_t{xs[i]} + 6,
                    300 + std::int64_t{ys[i]} + 6};
            }
            four.boundLeft = 210; four.boundTop = 310;
            four.boundRight = 312; four.boundBottom = 367;
            NativeRawChangedPixelWindow multiRgb{};
            multiRgb.capture(beforeMulti.data(), mw * 4u,
                             afterMulti.data(), mw * 4u, mw, mh);
            const NativeRawPresentTile full{0u, 0u, mw, mh, 200, 300};
            std::array<NativeRawPresentTile, 4> picks{};
            std::uint32_t count = 0u, totalRgb = 0u;
            for (; count < picks.size(); ++count) {
                std::uint32_t rgb = 0u;
                assert(native_raw_dirty_source_rgb_crop(
                    1920, 1080, four, full, multiRgb, picks[count],
                    rgb, count ? picks.data() : nullptr, count ? count : 1u));
                assert(rgb == 1u && native_raw_dirty_region_covers_tile(
                    1920, 1080, four, picks[count]));
                for (std::uint32_t j = 0u; j < count; ++j)
                    assert(native_raw_disjoint_present_tiles(picks[count], picks[j]));
                totalRgb += rgb;
            }
            assert(totalRgb == 4u);
            NativeRawPresentTile extra{};
            std::uint32_t extraRgb = 99u;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, four, full, multiRgb, extra, extraRgb,
                picks.data(), 4u) && extraRgb == 0u);
            // Reject an invalid exclusion budget and forged dirty bounds.
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, four, full, multiRgb, extra, extraRgb,
                picks.data(), 5u) && extraRgb == 0u);
            four.boundRight = 313;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, four, full, multiRgb, extra, extraRgb,
                picks.data(), 1u) && extraRgb == 0u);
            // A last island with only an alpha mutation is not RGB evidence.
            four.boundRight = 312;
            afterMulti[(ys[3] * mw + xs[3]) * 4u] = 0u;
            afterMulti[(ys[3] * mw + xs[3]) * 4u + 3u] = 255u;
            multiRgb.capture(beforeMulti.data(), mw * 4u,
                             afterMulti.data(), mw * 4u, mw, mh);
            // The other three still produce RGB, the fourth must not.
            count = 0u;
            for (; count < 3u; ++count) {
                std::uint32_t rgb = 0u;
                assert(native_raw_dirty_source_rgb_crop(
                    1920, 1080, four, full, multiRgb, picks[count],
                    rgb, count ? picks.data() : nullptr, count ? count : 1u));
                assert(rgb == 1u);
            }
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, four, full, multiRgb, extra, extraRgb,
                picks.data(), 3u) && extraRgb == 0u);
        }
        // Two disjoint authentic GPU PRE/POST sources may each contain TWO
        // separately repainted menu/car pixels. Retain both sources in one
        // exact-Present upload batch, not just one island per source.
        {
            constexpr std::uint32_t tw = 96u, th = 64u;
            std::array<std::uint8_t, tw * th * 4u> beforeA{}, beforeB{};
            auto afterA = beforeA, afterB = beforeB;
            afterA[(14u * tw + 12u) * 4u] = 21u;
            afterA[(14u * tw + 52u) * 4u + 1u] = 41u;
            afterB[(41u * tw + 12u) * 4u + 2u] = 61u;
            afterB[(41u * tw + 75u) * 4u] = 81u;
            NativeRawChangedPixelWindow rgbA{}, rgbB{};
            rgbA.capture(beforeA.data(), tw * 4u, afterA.data(), tw * 4u, tw, th);
            rgbB.capture(beforeB.data(), tw * 4u, afterB.data(), tw * 4u, tw, th);
            NativeRawPresentDirtyRegion repaint{};
            repaint.headerVerified = true;
            repaint.count = 4u;
            repaint.rectangles[0] = {208, 310, 216, 318};
            repaint.rectangles[1] = {248, 310, 256, 318};
            repaint.rectangles[2] = {408, 337, 416, 345};
            repaint.rectangles[3] = {471, 337, 479, 345};
            repaint.boundLeft = 208; repaint.boundTop = 310;
            repaint.boundRight = 479; repaint.boundBottom = 345;
            const NativeRawPresentTile sourceA{0u, 0u, tw, th, 200, 300};
            const NativeRawPresentTile sourceB{0u, 0u, tw, th, 400, 300};
            NativeRawSourceIslandBatch batch{};
            assert(batch.append(1920, 1080, repaint, sourceA, rgbA, false));
            assert(batch.append(1920, 1080, repaint, sourceB, rgbB, true));
            assert(batch.append(1920, 1080, repaint, sourceA, rgbA, false));
            assert(batch.append(1920, 1080, repaint, sourceB, rgbB, true));
            assert(batch.count == 4u && !batch.alternate[0] &&
                   batch.alternate[1] && !batch.alternate[2] &&
                   batch.alternate[3]);
            std::uint32_t total = 0u;
            for (std::uint32_t i = 0u; i < batch.count; ++i) {
                total += batch.rgbPixels[i];
                assert(batch.rgbPixels[i] == 1u);
                assert(native_raw_dirty_region_covers_tile(
                    1920, 1080, repaint, batch.tiles[i]));
                for (std::uint32_t j = 0u; j < i; ++j)
                    assert(native_raw_disjoint_present_tiles(
                        batch.tiles[i], batch.tiles[j]));
            }
            assert(total == 4u);
            assert(!batch.append(1920, 1080, repaint, sourceA, rgbA, false));
            repaint.boundRight = 480; // forged union is never eligible
            NativeRawSourceIslandBatch invalid{};
            assert(!invalid.append(1920, 1080, repaint, sourceA, rgbA, false));
            repaint.boundRight = 479;
            // Alpha-only writes cannot create the second source RGB island.
            afterB[(41u * tw + 75u) * 4u] = 0u;
            afterB[(41u * tw + 75u) * 4u + 3u] = 255u;
            rgbB.capture(beforeB.data(), tw * 4u, afterB.data(), tw * 4u, tw, th);
            NativeRawSourceIslandBatch three{};
            assert(three.append(1920, 1080, repaint, sourceA, rgbA, false));
            assert(three.append(1920, 1080, repaint, sourceB, rgbB, true));
            assert(three.append(1920, 1080, repaint, sourceA, rgbA, false));
            assert(!three.append(1920, 1080, repaint, sourceB, rgbB, true));
            assert(three.count == 3u);
        }
        // Alpha-only mutations must not create native RGB evidence.
        after[(22u * w + 65u) * 4u + 2u] = 0u;
        after[(22u * w + 65u) * 4u + 3u] = 255u;
        delta.capture(prior.data(), w * 4u, after.data(), w * 4u, w, h);
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, island, fullGpuTile, delta, cropped, realRgb));
        // Malformed dirty bounds or a disjoint repaint must fail closed.
        after[(22u * w + 65u) * 4u + 2u] = 201u;
        delta.capture(prior.data(), w * 4u, after.data(), w * 4u, w, h);
        island.boundRight = 174;
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, island, fullGpuTile, delta, cropped, realRgb));
        island.boundRight = 173;
        island.rectangles[0] = {400, 400, 413, 416};
        island.boundLeft = 400; island.boundTop = 400;
        island.boundRight = 413; island.boundBottom = 416;
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, island, fullGpuTile, delta, cropped, realRgb));
    }
    // Overlapping real Draw extents must not erase non-overlapping GPU RGB
    // contributions at their authentic original-game Present coordinates.
    {
        constexpr std::uint32_t w = 64u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto afterA = before, afterB = before;
        afterA[(10u * w + 8u) * 4u] = 71u;
        afterB[(10u * w + 55u) * 4u + 2u] = 91u;
        NativeRawChangedPixelWindow a{}, b{};
        a.capture(before.data(), w * 4u, afterA.data(), w * 4u, w, h);
        b.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true; dirty.count = 1u;
        dirty.rectangles[0] = {300, 400, 364, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 364; dirty.boundBottom = 432;
        const NativeRawPresentTile first{0u, 0u, 32u, 32u, 300, 400};
        const NativeRawPresentTile overlap{20u, 0u, 44u, 32u, 320, 400};
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920, 1080, dirty, first, a, false));
        assert(batch.append(1920, 1080, dirty, overlap, b, true));
        assert(batch.count == 2u && !batch.alternate[0] &&
               batch.alternate[1] && batch.tiles[1].destinationX == 332 &&
               batch.tiles[1].sourceX == 32u &&
               batch.tiles[1].copyWidth == 32u &&
               batch.rgbPixels[0] == 1u && batch.rgbPixels[1] == 1u &&
               native_raw_disjoint_present_tiles(batch.tiles[0], batch.tiles[1]));
        // Two previously uploaded islands divide a third authentic Draw
        // into three possible disjoint bands. The changed pixel survives.
        const NativeRawPresentTile used[2]{
            {0u, 0u, 20u, 32u, 320, 400},
            {0u, 0u, 8u, 32u, 356, 400}
        };
        NativeRawPresentTile remainder{};
        std::uint32_t rgb = 0u;
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty,
            NativeRawPresentTile{0u, 0u, 64u, 32u, 300, 400},
            b, remainder, rgb, used, 2u));
        assert(rgb == 1u && remainder.destinationX == 340 &&
               remainder.sourceX == 40u && remainder.copyWidth == 16u &&
               native_raw_disjoint_present_tiles(remainder, used[0]) &&
               native_raw_disjoint_present_tiles(remainder, used[1]));
        // Invalid old upload, forged dirty union and alpha-only changes
        // cannot make the later GPU region appear as valid game RGB.
        const NativeRawPresentTile foreign{0u, 0u, 12u, 8u, 1200, 400};
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, overlap, b, remainder, rgb, &foreign));
        dirty.boundRight = 365;
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, overlap, b, remainder, rgb,
            batch.tiles.data()));
        dirty.boundRight = 364;
        afterB[(10u * w + 55u) * 4u + 2u] = 0u;
        afterB[(10u * w + 55u) * 4u + 3u] = 255u;
        b.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, overlap, b, remainder, rgb,
            batch.tiles.data()));
    }
    // Overlapping live GPU Draw sample boxes need not overlap their actual
    // changed RGB. Preserve both authentic game source pixels, not just one.
    {
        constexpr std::uint32_t w = 64u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto afterA = before, afterB = before;
        afterA[(10u * w + 8u) * 4u] = 71u;
        afterB[(10u * w + 55u) * 4u + 2u] = 91u;
        NativeRawChangedPixelWindow rgbA{}, rgbB{};
        rgbA.capture(before.data(), w * 4u, afterA.data(), w * 4u, w, h);
        rgbB.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true; dirty.count = 1u;
        dirty.rectangles[0] = {300, 400, 364, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 364; dirty.boundBottom = 432;
        const NativeRawPresentTile source{0u, 0u, w, h, 300, 400};
        NativeRawSourceIslandBatch legacy{};
        assert(legacy.append(1920, 1080, dirty, source, rgbA, false));
        assert(!legacy.append(1920, 1080, dirty, source, rgbB, true));
        NativeRawSourceIslandBatch tight{};
        assert(tight.append(1920, 1080, dirty, source, rgbA, false, true));
        assert(tight.append(1920, 1080, dirty, source, rgbB, true, true));
        assert(tight.count == 2u && tight.rgbPixels[0] == 1u &&
               tight.rgbPixels[1] == 1u &&
               tight.tiles[0].sourceX == 8u &&
               tight.tiles[0].sourceY == 10u &&
               tight.tiles[0].destinationX == 308 &&
               tight.tiles[0].destinationY == 410 &&
               tight.tiles[0].copyWidth == 1u &&
               tight.tiles[0].copyHeight == 1u &&
               tight.tiles[1].sourceX == 55u &&
               tight.tiles[1].destinationX == 355 &&
               native_raw_disjoint_present_tiles(tight.tiles[0], tight.tiles[1]));
        // A 2x2 changed block retains all its authentic pixels and mapping.
        auto afterWide = before;
        for (std::uint32_t y = 18u; y < 20u; ++y)
            for (std::uint32_t x = 26u; x < 28u; ++x)
                afterWide[(y * w + x) * 4u + 1u] = 123u;
        NativeRawChangedPixelWindow rgbWide{};
        rgbWide.capture(before.data(), w * 4u,
                        afterWide.data(), w * 4u, w, h);
        NativeRawPresentTile bounded{};
        std::uint32_t realRgb = 0u;
        assert(rgbWide.tighten_to_rgb_bounds(source, bounded, realRgb));
        assert(realRgb == 4u && bounded.sourceX == 26u &&
               bounded.sourceY == 18u && bounded.destinationX == 326 &&
               bounded.destinationY == 418 && bounded.copyWidth == 2u &&
               bounded.copyHeight == 2u &&
               rgbWide.changed_pixels(bounded) == realRgb);
        assert(tight.append(1920, 1080, dirty, source, rgbWide, false, true));
        assert(!tight.append(1920, 1080, dirty, source, rgbWide, false, true));
        // Alpha-only content, forged source dirty geometry: fail closed.
        afterB[(10u * w + 55u) * 4u + 2u] = 0u;
        afterB[(10u * w + 55u) * 4u + 3u] = 255u;
        rgbB.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        NativeRawPresentTile alphaTile{};
        assert(!rgbB.tighten_to_rgb_bounds(source, alphaTile, realRgb));
        assert(realRgb == 0u);
        dirty.boundRight = 365;
        NativeRawSourceIslandBatch invalid{};
        assert(!invalid.append(1920, 1080, dirty, source,
                               rgbA, false, true));
    }
    // One genuine source Draw changes two separated RGB runs, while a
    // second native Draw changes a pixel INSIDE their sparse bounding box.
    // Preserve three genuine source contributions, in original coordinates,
    // without treating unchanged pixels as owned by the first Draw.
    {
        constexpr std::uint32_t w = 64u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto afterFirst = before, afterSecond = before;
        afterFirst[(9u * w + 7u) * 4u] = 71u;
        afterFirst[(9u * w + 51u) * 4u + 1u] = 61u;
        afterSecond[(9u * w + 29u) * 4u + 2u] = 91u;
        NativeRawChangedPixelWindow first{}, second{};
        first.capture(before.data(), w * 4u,
                      afterFirst.data(), w * 4u, w, h);
        second.capture(before.data(), w * 4u,
                       afterSecond.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true;
        dirty.count = 1u;
        dirty.rectangles[0] = {300, 400, 364, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 364; dirty.boundBottom = 432;
        const NativeRawPresentTile source{0u, 0u, w, h, 300, 400};
        NativeRawPresentTile enclosing{}, solid{};
        std::uint32_t pixels = 0u, denseRgb = 0u;
        assert(first.tighten_to_rgb_bounds(source, enclosing, pixels));
        assert(pixels == 2u && enclosing.copyWidth == 45u &&
               enclosing.copyHeight == 1u);
        assert(first.select_solid_rgb_tile(enclosing, solid, denseRgb));
        assert(denseRgb == 1u && solid.sourceX == 7u &&
               solid.destinationX == 307 && solid.destinationY == 409 &&
               solid.copyWidth == 1u);
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920, 1080, dirty, source, first, false, true));
        assert(batch.append(1920, 1080, dirty, source, second, true, true));
        assert(batch.append(1920, 1080, dirty, source, first, false, true));
        assert(batch.count == 3u && batch.rgbPixels[0] == 1u &&
               batch.rgbPixels[1] == 1u && batch.rgbPixels[2] == 1u &&
               batch.tiles[0].destinationX == 307 &&
               batch.tiles[1].destinationX == 329 &&
               batch.tiles[2].destinationX == 351);
        for (std::uint32_t i = 0u; i < batch.count; ++i) {
            assert(batch.tiles[i].destinationY == 409 &&
                   batch.tiles[i].copyWidth == 1u &&
                   batch.tiles[i].copyHeight == 1u);
            for (std::uint32_t j = 0u; j < i; ++j)
                assert(native_raw_disjoint_present_tiles(
                    batch.tiles[i], batch.tiles[j]));
        }
        assert(!batch.append(1920, 1080, dirty, source, first,
                             false, true));
        // Dense 2x2 source pixels remain one original-coordinate upload.
        auto wide = before;
        for (std::uint32_t y = 15u; y < 17u; ++y)
            for (std::uint32_t x = 33u; x < 35u; ++x)
                wide[(y * w + x) * 4u] = 142u;
        first.capture(before.data(), w * 4u, wide.data(), w * 4u, w, h);
        NativeRawSourceIslandBatch wideBatch{};
        assert(wideBatch.append(1920, 1080, dirty, source, first,
                                false, true));
        assert(wideBatch.count == 1u && wideBatch.rgbPixels[0] == 4u &&
               wideBatch.tiles[0].copyWidth == 2u &&
               wideBatch.tiles[0].copyHeight == 2u &&
               wideBatch.tiles[0].destinationX == 333 &&
               wideBatch.tiles[0].destinationY == 415);
        // Alpha-only Draw and forged D3D9 rcBound cannot borrow RGB proof.
        afterSecond = before;
        afterSecond[(9u * w + 29u) * 4u + 3u] = 255u;
        second.capture(before.data(), w * 4u,
                       afterSecond.data(), w * 4u, w, h);
        NativeRawPresentTile absent{};
        assert(!second.select_solid_rgb_tile(source, absent, denseRgb));
        assert(denseRgb == 0u);
        dirty.boundRight = 365;
        NativeRawSourceIslandBatch forged{};
        assert(!forged.append(1920, 1080, dirty, source,
                              first, false, true));
    }
    // A wide changed top row plus many narrower RGB rows must publish the
    // largest genuine GPU rectangle, not the first maximal horizontal run.
    // The latter misses one native row and wastes the four-island budget.
    {
        constexpr std::uint32_t w = 64u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto afterA = before, afterB = before;
        for (std::uint32_t x = 10u; x <= 20u; ++x)
            afterA[(10u * w + x) * 4u] = 111u;
        for (std::uint32_t y = 11u; y <= 17u; ++y)
            for (std::uint32_t x = 13u; x <= 17u; ++x)
                afterA[(y * w + x) * 4u + 1u] = 77u;
        afterB[(12u * w + 11u) * 4u + 2u] = 199u;
        NativeRawChangedPixelWindow a{}, b{};
        a.capture(before.data(), w * 4u, afterA.data(), w * 4u, w, h);
        b.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        const NativeRawPresentTile original{0u, 0u, w, h, 300, 400};
        NativeRawPresentTile solid{};
        std::uint32_t pixels = 0u;
        assert(a.select_solid_rgb_tile(original, solid, pixels));
        assert(pixels == 40u && solid.copyWidth == 5u &&
               solid.copyHeight == 8u && solid.sourceX == 13u &&
               solid.sourceY == 10u && solid.destinationX == 313 &&
               solid.destinationY == 410);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true;
        dirty.count = 1u;
        dirty.rectangles[0] = {300, 400, 364, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 364; dirty.boundBottom = 432;
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920, 1080, dirty, original, a, false, true));
        assert(batch.append(1920, 1080, dirty, original, b, true, true));
        assert(batch.count == 2u && batch.rgbPixels[0] == 40u &&
               batch.rgbPixels[1] == 1u &&
               batch.tiles[0].destinationX == 313 &&
               batch.tiles[1].destinationX == 311 &&
               batch.tiles[1].destinationY == 412 &&
               native_raw_disjoint_present_tiles(batch.tiles[0],
                                                 batch.tiles[1]));
        // Alpha alone is not a D3D11 RGB pixel; malformed game RGNDATA
        // must never become permission to overwrite the D3D9 Present.
        afterB = before;
        afterB[(12u * w + 11u) * 4u + 3u] = 255u;
        b.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        assert(!b.select_solid_rgb_tile(original, solid, pixels));
        dirty.boundRight = 365;
        NativeRawSourceIslandBatch forged{};
        assert(!forged.append(1920, 1080, dirty, original,
                              a, false, true));
    }
    // Two separated ORIGINAL D3D9 dirty menu panels: 20 scattered real
    // native RGB pixels on the first panel compete with a dense 4x4 real
    // GPU rectangle on the second. Sparse RGB-count selection (legacy)
    // chooses the first panel and later shrinks it to just one pixel.
    // The opt-in multi-Draw path must rank the final solid GPU upload and
    // retain all 16 authentic pixels in the second original screen panel.
    {
        constexpr std::uint32_t w = 80u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{}, after{};
        for (std::uint32_t y = 0u; y < 2u; ++y)
            for (std::uint32_t x = 0u; x < 10u; ++x)
                after[((1u + y * 3u) * w + x * 3u) * 4u] = 81u;
        for (std::uint32_t y = 10u; y < 14u; ++y)
            for (std::uint32_t x = 53u; x < 57u; ++x)
                after[(y * w + x) * 4u + 1u] = 193u;
        NativeRawChangedPixelWindow gpu{};
        gpu.capture(before.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true;
        dirty.count = 2u;
        dirty.rectangles[0] = {300, 400, 332, 432};
        dirty.rectangles[1] = {348, 400, 380, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 380; dirty.boundBottom = 432;
        const NativeRawPresentTile source{0u, 0u, w, h, 300, 400};
        NativeRawPresentTile legacy{}, dense{};
        std::uint32_t legacyRgb = 0u, denseRgb = 0u;
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, source, gpu, legacy, legacyRgb));
        assert(legacyRgb == 20u && legacy.destinationX == 300);
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, source, gpu, dense, denseRgb,
            nullptr, 1u, true));
        assert(denseRgb == 16u && dense.sourceX == 53u &&
               dense.sourceY == 10u && dense.destinationX == 353 &&
               dense.destinationY == 410 && dense.copyWidth == 4u &&
               dense.copyHeight == 4u &&
               native_raw_dirty_region_covers_tile(
                   1920, 1080, dirty, dense));
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920, 1080, dirty, source, gpu,
                            false, true));
        assert(batch.count == 1u && batch.rgbPixels[0] == 16u &&
               batch.tiles[0].destinationX == 353);
        // The remaining sparse panel can still contribute one unscaled
        // authentic RGB pixel; it never inherits the first panel's count.
        assert(batch.append(1920, 1080, dirty, source, gpu,
                            false, true));
        assert(batch.count == 2u && batch.rgbPixels[1] == 1u &&
               batch.tiles[1].destinationX >= 300 &&
               batch.tiles[1].destinationX < 332 &&
               native_raw_disjoint_present_tiles(
                   batch.tiles[0], batch.tiles[1]));
        // Alpha-only GPU output cannot displace the dense RGB evidence.
        auto alpha = after;
        for (std::uint32_t y = 10u; y < 14u; ++y)
            for (std::uint32_t x = 53u; x < 57u; ++x) {
                alpha[(y * w + x) * 4u + 1u] = 0u;
                alpha[(y * w + x) * 4u + 3u] = 255u;
            }
        gpu.capture(before.data(), w * 4u,
                    alpha.data(), w * 4u, w, h);
        NativeRawSourceIslandBatch alphaBatch{};
        assert(alphaBatch.append(1920, 1080, dirty, source, gpu,
                                 false, true));
        assert(alphaBatch.rgbPixels[0] == 1u &&
               alphaBatch.tiles[0].destinationX < 332);
        // Neither malformed rcBound nor a repaint-gap bridging rectangle
        // is allowed to publish even a genuine native GPU pixel.
        dirty.boundRight = 381;
        NativeRawSourceIslandBatch forged{};
        assert(!forged.append(1920, 1080, dirty, source, gpu,
                              false, true));
    }
    // A single real GPU capture can contain TWO separate native RGB repaint
    // panels farther apart than the legacy 24x24 preview window. Use the
    // entire physical capture (clipped to the actual D3D9 Present crop) to
    // recover both unscaled game-source islands. No invented RGB or holes.
    {
        constexpr std::uint32_t w = 96u, h = 64u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto after = before;
        for (std::uint32_t y = 25u; y < 29u; ++y)
            for (std::uint32_t x = 20u; x < 24u; ++x)
                after[(y * w + x) * 4u] = 31u;
        for (std::uint32_t y = 35u; y < 39u; ++y)
            for (std::uint32_t x = 70u; x < 74u; ++x)
                after[(y * w + x) * 4u + 2u] = 197u;
        NativeRawChangedPixelWindow gpu{};
        gpu.capture(before.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawPresentTile preview{0u, 0u, 24u, 24u, 0, 0};
        NativeRawPresentTile selected{};
        std::uint32_t previewPixels = 0u;
        assert(gpu.select(preview, selected, previewPixels));
        assert(previewPixels == 16u); // one window cannot reach both panels

        NativeRawPresentTile source{};
        assert(native_raw_source_capture_clip_tile(
            100u, 200u, w, h, 1920u, 1080u, 1920u, 1080u,
            115, 215, 180, 256, source));
        assert(source.sourceX == 15u && source.sourceY == 15u &&
               source.copyWidth == 65u && source.copyHeight == 41u &&
               source.destinationX == 115 && source.destinationY == 215);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true;
        dirty.count = 2u;
        dirty.rectangles[0] = {118, 221, 137, 240};
        dirty.rectangles[1] = {163, 230, 179, 253};
        dirty.boundLeft = 118; dirty.boundTop = 221;
        dirty.boundRight = 179; dirty.boundBottom = 253;
        assert(!native_raw_dirty_region_covers_tile(
            1920u, 1080u, dirty, source));
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920u, 1080u, dirty, source,
                            gpu, false, true));
        assert(batch.append(1920u, 1080u, dirty, source,
                            gpu, false, true));
        assert(batch.count == 2u && batch.rgbPixels[0] == 16u &&
               batch.rgbPixels[1] == 16u);
        assert(batch.tiles[0].destinationX == 120 &&
               batch.tiles[0].destinationY == 225 &&
               batch.tiles[1].destinationX == 170 &&
               batch.tiles[1].destinationY == 235 &&
               batch.tiles[0].sourceX == 20u &&
               batch.tiles[1].sourceX == 70u &&
               native_raw_disjoint_present_tiles(
                   batch.tiles[0], batch.tiles[1]));
        assert(!batch.append(1920u, 1080u, dirty, source,
                             gpu, false, true));
        // A crop without intersection, mismatched canonical game target,
        // capture outside source bounds, or forged D3D9 rcBound fails closed.
        assert(!native_raw_source_capture_clip_tile(
            100u, 200u, w, h, 1280u, 720u, 1920u, 1080u,
            115, 215, 180, 256, source));
        assert(source.copyWidth == 0u);
        assert(!native_raw_source_capture_clip_tile(
            1900u, 200u, w, h, 1920u, 1080u, 1920u, 1080u,
            115, 215, 180, 256, source));
        assert(!native_raw_source_capture_clip_tile(
            100u, 200u, w, h, 1920u, 1080u, 1920u, 1080u,
            200, 215, 210, 256, source));
        assert(native_raw_source_capture_clip_tile(
            100u, 200u, w, h, 1920u, 1080u, 1920u, 1080u,
            115, 215, 180, 256, source));
        dirty.boundRight = 180;
        NativeRawSourceIslandBatch forged{};
        assert(!forged.append(1920u, 1080u, dirty, source,
                              gpu, false, true));
        // An alpha-only second panel does not count as real GPU RGB.
        dirty.boundRight = 179;
        for (std::uint32_t y = 35u; y < 39u; ++y)
            for (std::uint32_t x = 70u; x < 74u; ++x) {
                after[(y * w + x) * 4u + 2u] = 0u;
                after[(y * w + x) * 4u + 3u] = 255u;
            }
        gpu.capture(before.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawSourceIslandBatch alpha{};
        assert(alpha.append(1920u, 1080u, dirty, source,
                            gpu, false, true));
        assert(!alpha.append(1920u, 1080u, dirty, source,
                             gpu, false, true));
        assert(alpha.count == 1u && alpha.rgbPixels[0] == 16u);
    }
    // A verified FULL original game Present has no dirty RGNDATA. It must
    // still show separate real GPU RGB geometry/color islands across the
    // physical source capture, without reserving gaps as native pixels.
    {
        constexpr std::uint32_t w = 96u, h = 64u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto after = before;
        for (std::uint32_t y = 10u; y < 14u; ++y)
            for (std::uint32_t x = 10u; x < 14u; ++x)
                after[(y * w + x) * 4u] = 21u;
        for (std::uint32_t y = 20u; y < 24u; ++y)
            for (std::uint32_t x = 40u; x < 44u; ++x)
                after[(y * w + x) * 4u + 1u] = 91u;
        for (std::uint32_t y = 35u; y < 39u; ++y)
            for (std::uint32_t x = 75u; x < 79u; ++x)
                after[(y * w + x) * 4u + 2u] = 174u;
        NativeRawChangedPixelWindow rgb{};
        rgb.capture(before.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion full{};
        assert(!native_raw_verified_full_source_crop_region(
            false, 1920u, 1080u, 100, 200, 300, 280, full));
        assert(!full.headerVerified && full.count == 0u);
        assert(!native_raw_verified_full_source_crop_region(
            true, 1920u, 1080u, 100, 200, 1921, 280, full));
        assert(!native_raw_verified_full_source_crop_region(
            true, 1920u, 1080u, 300, 200, 100, 280, full));
        assert(native_raw_verified_full_source_crop_region(
            true, 1920u, 1080u, 100, 200, 300, 280, full));
        NativeRawPresentTile source{};
        assert(native_raw_source_capture_clip_tile(
            105u, 205u, w, h, 1920u, 1080u, 1920u, 1080u,
            100, 200, 300, 280, source));
        NativeRawSourceIslandBatch batch{};
        for (std::uint32_t i = 0u; i < 3u; ++i)
            assert(batch.append(1920u, 1080u, full, source,
                                rgb, false, true));
        assert(!batch.append(1920u, 1080u, full, source,
                             rgb, false, true));
        assert(batch.count == 3u);
        assert(batch.tiles[0].destinationX == 115 &&
               batch.tiles[0].destinationY == 215 &&
               batch.tiles[1].destinationX == 145 &&
               batch.tiles[1].destinationY == 225 &&
               batch.tiles[2].destinationX == 180 &&
               batch.tiles[2].destinationY == 240);
        for (std::uint32_t i = 0u; i < 3u; ++i) {
            assert(batch.rgbPixels[i] == 16u);
            assert(batch.tiles[i].copyWidth == 4u &&
                   batch.tiles[i].copyHeight == 4u);
            assert(rgb.changed_pixels(batch.tiles[i]) == 16u);
        }
        // A verified partial crop is still clipped to original coordinates.
        NativeRawPresentDirtyRegion narrow{};
        assert(native_raw_verified_full_source_crop_region(
            true, 1920u, 1080u, 100, 200, 135, 225, narrow));
        NativeRawPresentTile narrowSource{};
        assert(native_raw_source_capture_clip_tile(
            105u, 205u, w, h, 1920u, 1080u, 1920u, 1080u,
            100, 200, 135, 225, narrowSource));
        NativeRawSourceIslandBatch onlyInside{};
        assert(onlyInside.append(1920u, 1080u, narrow,
                                 narrowSource, rgb, false, true));
        assert(!onlyInside.append(1920u, 1080u, narrow,
                                  narrowSource, rgb, false, true));
        assert(onlyInside.count == 1u && onlyInside.rgbPixels[0] == 16u);
        // An alpha-only Draw has no GPU RGB to present, full repaint or not.
        auto alpha = before;
        for (std::uint32_t y = 10u; y < 14u; ++y)
            for (std::uint32_t x = 10u; x < 14u; ++x)
                alpha[(y * w + x) * 4u + 3u] = 255u;
        rgb.capture(before.data(), w * 4u, alpha.data(), w * 4u, w, h);
        NativeRawSourceIslandBatch zero{};
        assert(!zero.append(1920u, 1080u, full, source,
                            rgb, false, true));
    }
    // Two authenticated GPU source byte orders yield identical displayed
    // D3D9 BGRA pixels, with XRGB opaque and ARGB alpha retained.
    const std::uint8_t nativeRgba[8]{17, 31, 241, 77, 9, 128, 255, 2};
    const std::uint8_t nativeBgra[8]{241, 31, 17, 77, 255, 128, 9, 2};
    std::uint8_t dst[8]{};
    native_raw_copy_to_d3d9_bgra(dst, nativeRgba, 2u,
                                 NativeRawColorByteOrder::Rgba, false);
    for (std::uint32_t i = 0u; i < 8u; ++i)
        assert(dst[i] == nativeBgra[i]);
    native_raw_copy_to_d3d9_bgra(dst, nativeBgra, 2u,
                                 NativeRawColorByteOrder::Bgra, true);
    for (std::uint32_t i = 0u; i < 8u; ++i)
        assert(dst[i] == (i % 4u == 3u ? 255u : nativeBgra[i]));
    native_raw_copy_to_d3d9_bgra(dst, nativeRgba, 2u,
                                 NativeRawColorByteOrder::Rgba, true);
    for (std::uint32_t i = 0u; i < 8u; ++i)
        assert(dst[i] == (i % 4u == 3u ? 255u : nativeBgra[i]));
    NativeRawDualTile t{};
    NativeRawDrawExtent fractional{};
    assert(native_raw_viewport_pixel_extent(3440, 1440,
        166.125f, 80.125f, 1.125f, 0.5f, fractional));
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        fractional, 2u, t));
    assert(t.first.x <= 167u && t.first.x + 256u >= 167u);
    assert(t.first.y <= 80u && t.first.y + 144u >= 80u);
    assert(!native_raw_viewport_pixel_extent(3440, 1440,
        3440.125f, 80.f, 1.f, 50.f, fractional));
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{0,0,3440,1440}, 0, t));
    assert(t.hasSecond);
    assert(t.first.x != t.second.x || t.first.y != t.second.y);
    assert(t.first.x + 256 <= 3440 && t.second.x + 256 <= 3440);
    assert(t.first.y + 144 <= 1440 && t.second.y + 144 <= 1440);
    assert(native_raw_source_tiles_disjoint(t.first, t.second, 256, 144));
    // Real 512x144 menu strip contains two exact disjoint GPU source
    // windows. A center-first sampler alone would falsely miss the pair.
    assert(native_raw_dual_draw_tile(512, 144, 256, 144,
        NativeRawDrawExtent{0, 0, 512, 144}, 0u, t));
    assert(t.hasSecond && t.first.x == 0u && t.second.x == 256u);
    assert(t.first.y == 0u && t.second.y == 0u);
    assert(native_raw_source_tiles_disjoint(t.first, t.second, 256, 144));
    // Regression order: evaluate two authenticated source regions before
    // the deliberate single-tile/no-overlap case changes hasSecond.
    assert(native_raw_choose_second_tile(0, 21, t.hasSecond));
    assert(!native_raw_choose_second_tile(21, 21, t.hasSecond));
    assert(!native_raw_choose_second_tile(21, 0, t.hasSecond));
    // Source-aligned Draw pixels outrank a displaced, denser legacy tile.
    // Retain the dual output only when final destinations are disjoint.
    {
        constexpr NativeRawPresentTile legacyFirst{0, 0, 64, 48, 100, 100};
        constexpr NativeRawPresentTile legacySecond{0, 0, 64, 48, 172, 100};
        constexpr NativeRawPresentTile alignedFirst{0, 0, 64, 48, 170, 100};
        constexpr NativeRawPresentTile alignedSecond{0, 0, 64, 48, 300, 100};
        static_assert(native_raw_can_show_source_aligned_pair(
            true, false, false, legacyFirst, legacySecond));
        static_assert(!native_raw_can_show_source_aligned_pair(
            true, true, false, alignedFirst, legacySecond));
        static_assert(native_raw_can_show_source_aligned_pair(
            false, true, true, alignedFirst, alignedSecond));
        // Source-coincident menu/vehicle repaint islands may clip two
        // independently completed GPU Draws to DIFFERENT sizes. The
        // previous equal-size pair predicate silently lost one draw.
        constexpr NativeRawPresentTile smallDirty{60, 20, 13, 16, 160, 220};
        constexpr NativeRawPresentTile largeDirty{51, 15, 18, 26, 356, 220};
        static_assert(native_raw_can_show_source_aligned_pair(
            false, true, true, smallDirty, largeDirty));
        static_assert(!native_raw_disjoint_equal_tiles(
            smallDirty, largeDirty));
        static_assert(!native_raw_can_show_source_aligned_pair(
            true, true, false, smallDirty, largeDirty));
        static_assert(!native_raw_can_show_source_aligned_pair(
            true, false, true, smallDirty, largeDirty));
        constexpr NativeRawPresentTile overlapDirty{51, 15, 18, 26, 165, 222};
        static_assert(!native_raw_can_show_source_aligned_pair(
            false, true, true, smallDirty, overlapDirty));
        constexpr NativeRawPresentTile emptyDirty{51, 15, 0, 26, 356, 220};
        static_assert(!native_raw_can_show_source_aligned_pair(
            false, true, true, smallDirty, emptyDirty));
        constexpr NativeRawPresentTile negativeDirty{51, 15, 18, 26, -1, 220};
        static_assert(!native_raw_can_show_source_aligned_pair(
            false, true, true, smallDirty, negativeDirty));
        static_assert(!native_raw_can_show_source_aligned_pair(
            false, true, false, alignedFirst, legacySecond));
        static_assert(native_raw_choose_source_aligned_second_tile(
            800u, 1u, false, true, true));
        static_assert(!native_raw_choose_source_aligned_second_tile(
            1u, 800u, true, false, true));
        static_assert(native_raw_choose_source_aligned_second_tile(
            1u, 800u, true, true, true));
        static_assert(!native_raw_choose_source_aligned_second_tile(
            800u, 1u, false, false, true));
        static_assert(!native_raw_choose_source_aligned_second_tile(
            1u, 800u, false, true, false));
    }
    // A narrow source raster can intersect multiple nominal tile origins,
    // but the same GPU RGB bytes must NEVER count as two native Draw tiles.
    assert(native_raw_dual_draw_tile(640, 480, 256, 144,
        NativeRawDrawExtent{100, 100, 180, 180}, 0u, t));
    assert(!t.hasSecond);
    assert(!native_raw_source_tiles_disjoint(
        NativeRawTileOrigin{0, 0}, NativeRawTileOrigin{120, 50}, 256, 144));
    assert(native_raw_source_tiles_disjoint(
        NativeRawTileOrigin{0, 0}, NativeRawTileOrigin{256, 20}, 256, 144));
    assert(!native_raw_source_tiles_disjoint(
        NativeRawTileOrigin{0, 0}, NativeRawTileOrigin{1, 1}, 0, 144));
    assert(native_raw_dual_draw_tile(256, 144, 256, 144,
        NativeRawDrawExtent{0,0,256,144}, 3, t));
    assert(!t.hasSecond && !native_raw_choose_second_tile(0, 1, t.hasSecond));
    assert(!native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{100,100,100,200}, 0, t));
    assert(!t.hasSecond);
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{100,100,900,600}, 4, t));
    assert(t.hasSecond);
    // A source color fill that only overlaps the alternate GPU tile
    // must revoke the entire pair. Unknown/full writes remain fail closed.
    constexpr NativeRawSourcePixelRect onlySecond[] = {{500, 500, 650, 650}};
    constexpr NativeRawSourcePixelRect noHit[] = {{0, 0, 80, 80}};
    constexpr NativeRawSourcePixelRect onlyFirst[] = {{105, 105, 140, 140}};
    assert(native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, onlySecond, 1));
    assert(native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, onlyFirst, 1));
    assert(!native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, noHit, 1));
    assert(!native_raw_dual_source_write_overlaps(
        100, 100, false, 500, 500, 256, 144, onlySecond, 1));
    assert(native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, nullptr, 0));
    assert(native_raw_dual_source_write_overlaps(
        0xffffffffu, 0, true, 500, 500, 256, 144, noHit, 1));
    // Distinct game-visible RAW regions: large desktop supports side by
    // side; narrow menus may use vertical placement; tiny crop fails closed.
    NativeRawPresentTile primary{}, secondary{};
    assert(native_raw_partial_present_tile(800, 450, 0, 0, 800, 450,
                                          256, 144, primary));
    assert(native_raw_secondary_present_tile(primary, 0, 0, 800, 450,
                                             secondary));
    assert(secondary.destinationX + secondary.copyWidth + 8 ==
           primary.destinationX);
    assert(secondary.destinationY == primary.destinationY);
    assert(native_raw_partial_present_tile(300, 440, 0, 0, 300, 440,
                                          256, 144, primary));
    assert(native_raw_secondary_present_tile(primary, 0, 0, 300, 440,
                                             secondary));
    assert(secondary.destinationX == primary.destinationX);
    assert(secondary.destinationY ==
           primary.destinationY + primary.copyHeight + 8);
    assert(native_raw_partial_present_tile(300, 185, 0, 0, 300, 185,
                                          256, 144, primary));
    assert(!native_raw_secondary_present_tile(primary, 0, 0, 300, 185,
                                              secondary));
    assert(!native_raw_secondary_present_tile(
        NativeRawPresentTile{}, 0, 0, 800, 450, secondary));
    assert(!native_raw_secondary_present_tile(
        NativeRawPresentTile{0, 0, 256, 144, -2, 8},
        0, 0, 800, 450, secondary));

    // End-to-end compact actual GPU staging + RGB-window crop path: a
    // 96x64 menu target must not be rejected by the old 256x144 minimum.
    constexpr std::uint32_t compactW = 96u, compactH = 64u;
    assert(native_raw_dual_draw_tile(compactW, compactH, compactW, compactH,
        NativeRawDrawExtent{0, 0, 96, 64}, 0u, t));
    assert(!t.hasSecond && t.first.x == 0u && t.first.y == 0u);
    NativeRawChangedPixelWindow changedWindow{};
    std::array<std::uint8_t, compactW * compactH * 4u> before{};
    auto after = before;
    after[(60u * compactW + 94u) * 4u + 0u] = 213u;
    // A restricted source crop can still select a real edge RGB pixel.
    NativeRawPresentTile compactOriginal{};
    NativeRawPresentTile compactSelected{};
    std::uint32_t realPixels = 0u;
    assert(native_raw_partial_present_tile(
        88, 58, 0, 0, 88, 58, compactW, compactH, compactOriginal));
    changedWindow.capture(before.data(), compactW * 4u,
                          after.data(), compactW * 4u, compactW, compactH);
    assert(changedWindow.select(compactOriginal, compactSelected, realPixels));
    assert(realPixels == 1u);
    // Real split 30x30 menu dirty repaint: 96x64 native GPU capture
    // now reaches the D3D9 source crop without guessed/upscaled pixels.
    NativeRawPresentDirtyRegion narrow{};
    narrow.headerVerified = true;
    narrow.count = 2u;
    narrow.rectangles[0] = {100, 120, 130, 135};
    narrow.rectangles[1] = {100, 135, 130, 150};
    narrow.boundLeft = 100; narrow.boundTop = 120;
    narrow.boundRight = 130; narrow.boundBottom = 150;
    NativeRawPresentTile tight{}, gpuCrop{};
    assert(native_raw_dirty_region_place_tile(
        1920, 1080, 0, 0, 1920, 1080, narrow,
        compactW, compactH, tight, nullptr, true));
    assert(tight.copyWidth == 24u && tight.copyHeight == 24u);
    assert(native_raw_dirty_region_covers_tile(1920, 1080, narrow, tight));
    assert(changedWindow.select(tight, gpuCrop, realPixels));
    assert(realPixels == 1u && gpuCrop.sourceX <= 94u &&
           gpuCrop.sourceX + gpuCrop.copyWidth > 94u);
    // One missing original-game dirty row never grants publication.
    narrow.rectangles[1].top = 136;
    assert(!native_raw_dirty_region_place_tile(
        1920, 1080, 0, 0, 1920, 1080, narrow,
        compactW, compactH, tight, nullptr, true));
    assert(compactSelected.sourceX <= 94u &&
           compactSelected.sourceX + compactSelected.copyWidth > 94u);
    assert(compactSelected.sourceY <= 60u &&
           compactSelected.sourceY + compactSelected.copyHeight > 60u);
    // Invalid pitch, zero dimensions or unsupported larger GPU extents
    // cannot turn stale prefix data into a visible native pixel.
    changedWindow.capture(before.data(), 3u, after.data(), compactW * 4u,
                          compactW, compactH);
    assert(!changedWindow.select(compactOriginal, compactSelected, realPixels));
    changedWindow.capture(before.data(), compactW * 4u,
                          after.data(), compactW * 4u, 257u, compactH);
    assert(!changedWindow.select(compactOriginal, compactSelected, realPixels));


    // Real source RGB panels can be much smaller than the 256x144 mapped
    // GPU copy. A D3D9 UpdateSurface only consumes this island source RECT;
    // modifying other staging bytes is wasted work and must not be required.
    // Probe both RGBA/BGRA, padded pitches, magenta incomplete borders,
    // alpha-only pixels, a second disjoint panel, and fail-closed bounds.
    {
        constexpr std::uint32_t w = 14u, h = 12u;
        constexpr std::size_t sourcePitch = w * 4u + 4u;
        constexpr std::size_t dstPitch = w * 4u + 8u;
        std::array<std::uint8_t, sourcePitch * h> before{}, after{};
        std::array<std::uint8_t, dstPitch * h> output{};
        const auto rgba = [&](std::uint32_t x, std::uint32_t y,
                              std::uint8_t r, std::uint8_t g,
                              std::uint8_t b, std::uint8_t a) {
            auto* pixel = after.data() + y * sourcePitch + x * 4u;
            pixel[0] = r; pixel[1] = g; pixel[2] = b; pixel[3] = a;
        };
        const NativeRawPresentTile panel{2u, 1u, 10u, 10u, 100, 200};
        rgba(2u, 1u, 90u, 60u, 40u, 80u); // changed REAL border pixel
        rgba(6u, 6u, 10u, 20u, 30u, 40u); // changed inner pixel
        rgba(7u, 6u, 0u, 0u, 0u, 40u); // alpha-only is NOT RGB evidence
        output.fill(0x5au);
        assert(native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, panel,
            NativeRawColorByteOrder::Rgba, false));
        const auto pixel = [&](std::uint32_t x, std::uint32_t y) {
            return output.data() + y * dstPitch + x * 4u;
        };
        assert(pixel(2u, 1u)[0] == 40u &&
               pixel(2u, 1u)[1] == 60u &&
               pixel(2u, 1u)[2] == 90u &&
               pixel(2u, 1u)[3] == 80u);
        assert(pixel(6u, 6u)[0] == 30u &&
               pixel(6u, 6u)[1] == 20u &&
               pixel(6u, 6u)[2] == 10u &&
               pixel(6u, 6u)[3] == 40u);
        assert(pixel(3u, 2u)[0] == 255u &&
               pixel(3u, 2u)[1] == 0u &&
               pixel(3u, 2u)[2] == 255u); // incomplete border
        assert(pixel(7u, 6u)[0] == 0u &&
               pixel(7u, 6u)[1] == 0u &&
               pixel(7u, 6u)[2] == 0u &&
               pixel(7u, 6u)[3] == 40u);
        assert(pixel(0u, 0u)[0] == 0x5au &&
               pixel(13u, 11u)[0] == 0x5au);
        // Another independent source-aligned panel on the same D3D9
        // staging buffer must not change the first/other-pixel receipts.
        rgba(12u, 10u, 51u, 52u, 53u, 54u);
        const NativeRawPresentTile other{12u, 10u, 2u, 2u, 400, 200};
        assert(native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, other,
            NativeRawColorByteOrder::Bgra, true));
        assert(pixel(12u, 10u)[0] == 51u &&
               pixel(12u, 10u)[1] == 52u &&
               pixel(12u, 10u)[2] == 53u &&
               pixel(12u, 10u)[3] == 255u);
        assert(pixel(6u, 6u)[0] == 30u &&
               pixel(6u, 6u)[2] == 10u);
        // Incomplete or invalid native source extents cannot stage even
        // one pixel, and no destination byte is touched on failure.
        const auto priorOutput = output;
        NativeRawPresentTile invalid = other;
        invalid.copyWidth = 3u; // extends beyond GPU readback
        assert(!native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, invalid,
            NativeRawColorByteOrder::Bgra, false));
        assert(!native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), 8u,
            after.data(), sourcePitch, w, h, other,
            NativeRawColorByteOrder::Bgra, false));
        assert(!native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, NativeRawPresentTile{},
            NativeRawColorByteOrder::Bgra, false));
        assert(output == priorOutput);
    }

}
