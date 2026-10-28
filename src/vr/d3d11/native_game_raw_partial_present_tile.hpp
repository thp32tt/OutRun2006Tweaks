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
    NativeRawPresentTile& out) noexcept {
    out = {};
    constexpr std::int64_t kMargin = 8;
    constexpr std::uint32_t kMinPixels = 24;
    constexpr auto kMaxLong =
        static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)());
    if (!backWidth || !backHeight || backWidth > kMaxLong ||
        backHeight > kMaxLong || tileWidth < kMinPixels ||
        tileHeight < kMinPixels || left < 0 || top < 0 ||
        left >= right || top >= bottom ||
        right > backWidth || bottom > backHeight ||
        right - left < 2 * kMargin + kMinPixels ||
        bottom - top < 2 * kMargin + kMinPixels)
        return false;
    const auto width = static_cast<std::uint32_t>((std::min)(
        std::int64_t{tileWidth}, right - left - 2 * kMargin));
    const auto height = static_cast<std::uint32_t>((std::min)(
        std::int64_t{tileHeight}, bottom - top - 2 * kMargin));
    out.sourceX = (tileWidth - width) / 2u;
    out.sourceY = (tileHeight - height) / 2u;
    out.copyWidth = width;
    out.copyHeight = height;
    out.destinationX = right - kMargin - width;
    out.destinationY = top + kMargin;
    return out.destinationX >= left + kMargin &&
           out.destinationY + height <= bottom - kMargin;
}
} // namespace outrun::vr::dx11
