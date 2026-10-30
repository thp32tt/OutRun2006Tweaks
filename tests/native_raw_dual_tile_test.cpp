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

}
