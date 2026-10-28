// Native RAW display must show the richest genuine shader-bound GPU output,
// not just one center pixel while an entire vehicle/menu fragment is elsewhere.
// This diagnostic remains source-crop bounded and cannot certify gameplay.
#include "../src/vr/d3d11/native_game_raw_changed_pixel_window.hpp"
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
}
