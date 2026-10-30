#pragma once
// Unscaled D3D11 Draw diagnostic subset for authentic cropped D3D9 Presents.
// Never promote a partial tile to an entire game frame or stereo eye.
#include <algorithm>
#include <cstdint>
#include <limits>
namespace outrun::vr::dx11 {
struct NativeRawPresentTile {
    std::uint32_t sourceX{}, sourceY{}, copyWidth{}, copyHeight{};
    std::int64_t destinationX{}, destinationY{};
};
[[nodiscard]] constexpr bool native_raw_partial_present_tile(
    std::uint32_t backWidth, std::uint32_t backHeight,
    std::int64_t left, std::int64_t top,
    std::int64_t right, std::int64_t bottom,
    std::uint32_t tileWidth, std::uint32_t tileHeight,
    NativeRawPresentTile& out,
    bool allowCompactRaw = false) noexcept {
    out = {};
    // Tight original D3D9 menu/car dirty crops can be 24..39 pixels.
    // Keep the unscaled GPU source and shrink only the label margin.
    constexpr std::int64_t kMargin = 8;
    constexpr std::uint32_t kMinPixels = 24;
    // Existing regular RAW 256x144 diagnostic windows retain the original
    // 40px minimum. Only explicit genuine SMALL GPU target paths may relax
    // the margin, without weakening legacy dirty Present admission.
    const bool compact = allowCompactRaw &&
        (tileWidth < 256u || tileHeight < 144u);
    const auto minSpan = static_cast<std::int64_t>(
        kMinPixels + (compact ? 0u : 2u * static_cast<std::uint32_t>(kMargin)));
    constexpr auto kMaxLong =
        static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)());
    if (!backWidth || !backHeight || backWidth > kMaxLong ||
        backHeight > kMaxLong || tileWidth < kMinPixels ||
        tileHeight < kMinPixels || left < 0 || top < 0 ||
        left >= right || top >= bottom ||
        right > backWidth || bottom > backHeight ||
        right - left < minSpan || bottom - top < minSpan)
        return false;
    // A 24px repaint permits zero destination margin; a >=40px repaint
    // retains the original 8px experimental frame. No pixel is scaled.
    const auto marginX = compact ? (std::min)(kMargin,
        (right - left - kMinPixels) / 2) : kMargin;
    const auto marginY = compact ? (std::min)(kMargin,
        (bottom - top - kMinPixels) / 2) : kMargin;
    const auto width = static_cast<std::uint32_t>((std::min)(
        std::int64_t{tileWidth}, right - left - 2 * marginX));
    const auto height = static_cast<std::uint32_t>((std::min)(
        std::int64_t{tileHeight}, bottom - top - 2 * marginY));
    out.sourceX = (tileWidth - width) / 2u;
    out.sourceY = (tileHeight - height) / 2u;
    out.copyWidth = width;
    out.copyHeight = height;
    out.destinationX = right - marginX - width;
    out.destinationY = top + marginY;
    return out.destinationX >= left + marginX &&
           out.destinationY + height <= bottom - marginY;
}

 // A verified 24..39px source repaint can contain REAL menu/HUD RGB even
 // when the native GPU capture is the ordinary 256x144 size. This is NOT a
 // displaced diagnostic inset: the caller must separately prove canonical
 // D3D9 Draw/Present surface identity and forbid the legacy upload fallback.
 // The bounded preview only provides a legal starting window for the full
 // source-aligned PRE/POST RGB island scan.
 [[nodiscard]] constexpr bool native_raw_verified_small_source_present_tile(
     bool fullCropRepaintVerified,
     std::uint32_t backWidth, std::uint32_t backHeight,
     std::int64_t left, std::int64_t top,
     std::int64_t right, std::int64_t bottom,
     std::uint32_t captureWidth, std::uint32_t captureHeight,
     NativeRawPresentTile& out) noexcept {
     out = {};
     constexpr auto kMaxDim = static_cast<std::uint32_t>(
         (std::numeric_limits<std::int32_t>::max)());
     if (!fullCropRepaintVerified || !backWidth || !backHeight ||
         backWidth > kMaxDim || backHeight > kMaxDim ||
         captureWidth < 24u || captureHeight < 24u ||
         left < 0 || top < 0 || right <= left || bottom <= top ||
         right > backWidth || bottom > backHeight)
         return false;
     const auto cropW = right - left, cropH = bottom - top;
     if (cropW < 24 || cropH < 24 ||
         (cropW >= 40 && cropH >= 40))
         return false;
     const auto width = static_cast<std::uint32_t>((std::min)(
         std::int64_t{captureWidth}, cropW));
     const auto height = static_cast<std::uint32_t>((std::min)(
         std::int64_t{captureHeight}, cropH));
     out.sourceX = (captureWidth - width) / 2u;
     out.sourceY = (captureHeight - height) / 2u;
     out.copyWidth = width;
     out.copyHeight = height;
     out.destinationX = left;
     out.destinationY = top;
     return true;
 }
// When a real GPU Draw changed pixels away from the initially centered
// source subsection, move the RAW diagnostic crop to those authentic pixels.
// A source pixel never becomes a guessed/extrapolated destination pixel.
[[nodiscard]] constexpr bool native_raw_retarget_present_tile(
    const NativeRawPresentTile& original, std::uint32_t tileWidth,
    std::uint32_t tileHeight, std::uint32_t changedX,
    std::uint32_t changedY, NativeRawPresentTile& out) noexcept {
    out = {};
    if (!original.copyWidth || !original.copyHeight ||
        original.copyWidth > tileWidth || original.copyHeight > tileHeight ||
        original.sourceX > tileWidth - original.copyWidth ||
        original.sourceY > tileHeight - original.copyHeight ||
        changedX >= tileWidth || changedY >= tileHeight)
        return false;
    out = original;
    const auto centeredX = changedX > original.copyWidth / 2u
        ? changedX - original.copyWidth / 2u : 0u;
    const auto centeredY = changedY > original.copyHeight / 2u
        ? changedY - original.copyHeight / 2u : 0u;
    out.sourceX = (std::min)(centeredX, tileWidth - original.copyWidth);
    out.sourceY = (std::min)(centeredY, tileHeight - original.copyHeight);
    return changedX >= out.sourceX &&
           changedX - out.sourceX < out.copyWidth &&
           changedY >= out.sourceY &&
           changedY - out.sourceY < out.copyHeight;
}
// Magenta INCOMPLETE frame labels an unconverted picture. Preserve genuine
// GPU-changed RGB even at that frame, or a single edge fragment could be
// entirely painted over and falsely counted as visible native Draw pixels.
[[nodiscard]] constexpr bool native_raw_present_border_pixel(
    const NativeRawPresentTile& tile, std::uint32_t x, std::uint32_t y,
    bool genuineGpuRgbChanged) noexcept {
    if (genuineGpuRgbChanged || x < tile.sourceX || y < tile.sourceY ||
        x - tile.sourceX >= tile.copyWidth ||
        y - tile.sourceY >= tile.copyHeight)
        return false;
    const auto dx = x - tile.sourceX;
    const auto dy = y - tile.sourceY;
    return dx < 3u || tile.copyWidth - dx <= 3u ||
           dy < 4u || tile.copyHeight - dy <= 4u;
}
} // namespace outrun::vr::dx11
