// Native RAW display must show the richest genuine shader-bound GPU output,
// not just one center pixel while an entire vehicle/menu fragment is elsewhere.
// This diagnostic remains source-crop bounded and cannot certify gameplay.
#include "../src/vr/d3d11/native_game_raw_changed_pixel_window.hpp"
#include "../src/vr/d3d11/native_game_raw_present_coverage.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11;
int main() {
    constexpr std::uint32_t W = NativeRawChangedPixelWindow::kWidth;
    constexpr std::uint32_t H = NativeRawChangedPixelWindow::kHeight;
    std::array<std::uint8_t, W*H*4u> before{}, after{};
    NativeRawChangedPixelWindow chooser;
    NativeRawPresentTile original{}, selected{};
    std::uint32_t changed = 0u;
    assert(native_raw_partial_present_tile(1920u, 1080u, 700, 300,
                                           748, 348, W, H, original));
    const auto initialX = original.sourceX;
    const auto initialY = original.sourceY;
    // A single middle fragment is NOT enough reason to hide a much richer
    // authentic native GPU Draw at the edge of the intercepted viewport.
    after[(70u * W + 120u) * 4u] = 120u;
    for (std::uint32_t y = 100u; y < 108u; ++y)
        for (std::uint32_t x = 200u; x < 208u; ++x)
            after[(y * W + x) * 4u + 1u] = 210u;
    chooser.capture(before.data(), W*4u, after.data(), W*4u);
    assert(chooser.select(original, selected, changed));
    assert(changed == 64u);
    assert(selected.sourceX <= 200u && selected.sourceX + selected.copyWidth >= 208u);
    assert(selected.sourceY <= 100u && selected.sourceY + selected.copyHeight >= 108u);
    assert(selected.destinationX == original.destinationX);
    assert(selected.destinationY == original.destinationY);
    assert(!native_raw_present_border_pixel(selected, 200u, 100u, true));
    // Empty/unchanged GPU result is NEVER counted as visible Draw pixels.
    after.fill(0u);
    chooser.capture(before.data(), W*4u, after.data(), W*4u);
    assert(chooser.select(original, selected, changed));
    assert(changed == 0u && selected.sourceX == initialX &&
           selected.sourceY == initialY);
    // One source-authentic pixel in the original crop does not jitter a tie.
    after[(70u * W + 120u) * 4u] = 255u;
    chooser.capture(before.data(), W*4u, after.data(), W*4u);
    assert(chooser.select(original, selected, changed));
    assert(changed == 1u && selected.sourceX == initialX &&
           selected.sourceY == initialY);
    // Alpha-only changes are not evidence of a visible native RGB pixel.
    after.fill(0u);
    after[(70u * W + 120u) * 4u + 3u] = 255u;
    chooser.capture(before.data(), W*4u, after.data(), W*4u);
    assert(chooser.select(original, selected, changed) && changed == 0u);
    // Reject an impossible source tile rather than reading beyond staging.
    NativeRawPresentTile bad = original;
    bad.sourceX = W;
    assert(!chooser.select(bad, selected, changed));
    assert(changed == 0u && selected.copyWidth == 0u);
    // End-to-end portable pixel behavior: a fragmented dirty union with a
    // narrow attached tail must carry the REAL off-center GPU RGB window.
    NativeRawPresentDirtyRegion dirty{};
    dirty.headerVerified = true;
    dirty.count = 4u;
    dirty.boundLeft = 600; dirty.boundTop = 300;
    dirty.boundRight = 900; dirty.boundBottom = 348;
    dirty.rectangles[0] = {600, 300, 616, 348};
    dirty.rectangles[1] = {616, 300, 632, 348};
    dirty.rectangles[2] = {632, 300, 648, 348};
    dirty.rectangles[3] = {648, 300, 900, 308};
    assert(native_raw_dirty_region_place_tile(
        1920, 1080, 0, 0, 1920, 1080, dirty, W, H, original));
    after.fill(0u);
    for (std::uint32_t y = 100u; y < 108u; ++y)
        for (std::uint32_t x = 200u; x < 208u; ++x)
            after[(y * W + x) * 4u + 1u] = 210u;
    chooser.capture(before.data(), W*4u, after.data(), W*4u);
    assert(chooser.select(original, selected, changed));
    assert(changed == 64u);
    assert(selected.copyWidth == 32u && selected.copyHeight == 32u);
    assert(native_raw_dirty_region_covers_tile(1920, 1080, dirty, selected));
    // Simulate the exact unscaled source window and RAW border operation.
    // All 64 genuine GPU pixels survive at real painted destinations.
    std::uint32_t displayedRgb = 0u;
    for (std::uint32_t y = 0; y < selected.copyHeight; ++y)
        for (std::uint32_t x = 0; x < selected.copyWidth; ++x) {
            const auto sx = selected.sourceX + x, sy = selected.sourceY + y;
            const auto offset = (sy * W + sx) * 4u;
            const bool genuine = native_raw_rgb_changed(
                before.data() + offset, after.data() + offset);
            if (genuine) {
                assert(!native_raw_present_border_pixel(selected, sx, sy, true));
                ++displayedRgb;
            }
            assert(selected.destinationX + x >= 600 &&
                   selected.destinationX + x < 648);
            assert(selected.destinationY + y >= 300 &&
                   selected.destinationY + y < 348);
        }
    assert(displayedRgb == changed);
    // Alpha-only output never becomes visible RGB evidence after placement.
    after.fill(0u);
    after[(100u * W + 200u) * 4u + 3u] = 255u;
    chooser.capture(before.data(), W*4u, after.data(), W*4u);
    assert(chooser.select(original, selected, changed) && changed == 0u);
    dirty.rectangles[1].left = 617;
    assert(!native_raw_dirty_region_place_tile(
        1920, 1080, 0, 0, 1920, 1080, dirty, W, H, original));
    // End-to-end source-to-RGB crop across vertically stacked D3D9
    // repaint rows. No generated pixels, repaint widening or scaling.
    dirty.rectangles[0] = {600, 300, 648, 316};
    dirty.rectangles[1] = {600, 316, 648, 332};
    dirty.rectangles[2] = {600, 332, 648, 348};
    dirty.rectangles[3] = {648, 332, 900, 340};
    assert(native_raw_dirty_region_place_tile(
        1920, 1080, 0, 0, 1920, 1080, dirty, W, H, original));
    assert(original.copyWidth == 32u && original.copyHeight == 32u);
    assert(original.destinationX == 608 && original.destinationY == 308);
    after.fill(0u);
    for (std::uint32_t y = 100u; y < 108u; ++y)
        for (std::uint32_t x = 200u; x < 208u; ++x)
            after[(y * W + x) * 4u + 2u] = 170u;
    chooser.capture(before.data(), W*4u, after.data(), W*4u);
    assert(chooser.select(original, selected, changed) && changed == 64u);
    assert(selected.copyWidth == 32u && selected.copyHeight == 32u);
    assert(native_raw_dirty_region_covers_tile(1920, 1080, dirty, selected));
    std::uint32_t shownRgb = 0u;
    for (std::uint32_t y = 0u; y < selected.copyHeight; ++y)
        for (std::uint32_t x = 0u; x < selected.copyWidth; ++x) {
            const auto sx = selected.sourceX + x, sy = selected.sourceY + y;
            const auto off = (sy * W + sx) * 4u;
            if (native_raw_rgb_changed(
                    before.data() + off, after.data() + off)) {
                assert(!native_raw_present_border_pixel(selected, sx, sy, true));
                ++shownRgb;
            }
        }
    assert(shownRgb == changed);
    // A single uncovered source row cannot inherit the valid GPU count.
    dirty.rectangles[1].top = 317;
    assert(!native_raw_dirty_region_covers_tile(
        1920, 1080, dirty, selected));
    // Complete source-to-visible native GPU crop for a 2D-fragmented
    // repaint. This was previously rejected when neither one-axis strip
    // sweep could place the tile around an attached skinny update.
    dirty = {};
    dirty.headerVerified = true;
    dirty.count = 10u;
    dirty.boundLeft = 600; dirty.boundTop = 300;
    dirty.boundRight = 900; dirty.boundBottom = 348;
    for (std::uint32_t row = 0u; row < 3u; ++row)
        for (std::uint32_t col = 0u; col < 3u; ++col) {
            const auto x = std::int64_t{600} + std::int64_t{16} * col;
            const auto y = std::int64_t{300} + std::int64_t{16} * row;
            dirty.rectangles[row * 3u + col] = {x, y, x + 16, y + 16};
        }
    dirty.rectangles[9] = {648, 300, 900, 308};
    assert(native_raw_dirty_region_place_tile(
        1920, 1080, 0, 0, 1920, 1080, dirty, W, H, original));
    assert(original.copyWidth == 32u && original.copyHeight == 32u);
    assert(original.destinationX == 608 && original.destinationY == 308);
    after.fill(0u);
    for (std::uint32_t y = 100u; y < 108u; ++y)
        for (std::uint32_t x = 200u; x < 208u; ++x)
            after[(y * W + x) * 4u + 1u] = 190u;
    chooser.capture(before.data(), W * 4u, after.data(), W * 4u);
    assert(chooser.select(original, selected, changed) && changed == 64u);
    assert(native_raw_dirty_region_covers_tile(1920, 1080, dirty, selected));
    std::uint32_t actualGpuRgb = 0u;
    for (std::uint32_t y = 0u; y < selected.copyHeight; ++y)
        for (std::uint32_t x = 0u; x < selected.copyWidth; ++x) {
            const auto sx = selected.sourceX + x, sy = selected.sourceY + y;
            const auto off = (sy * W + sx) * 4u;
            if (native_raw_rgb_changed(before.data() + off,
                                       after.data() + off)) {
                assert(!native_raw_present_border_pixel(
                    selected, sx, sy, true));
                ++actualGpuRgb;
            }
        }
    assert(actualGpuRgb == 64u);
    dirty.rectangles[4].left = 617;
    assert(!native_raw_dirty_region_covers_tile(
        1920, 1080, dirty, selected));

}

