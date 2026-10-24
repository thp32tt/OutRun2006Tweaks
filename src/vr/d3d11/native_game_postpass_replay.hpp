#pragma once
#include <cstdint>

namespace outrun::vr::dx11 {
// One exact camera mip/array admission for game-authored Copy/Stretch
// preflight AND native GPU encoder: neither eye may enqueue commands if
// its box would address bytes beyond the selected physical mip.
struct NativeGamePostpassMipExtent {
    std::uint32_t width{}, height{};
    bool valid{};
};
[[nodiscard]] constexpr NativeGamePostpassMipExtent
native_game_postpass_mip_extent(
    std::uint32_t width, std::uint32_t height,
    std::uint32_t mipLevels, std::uint32_t mip,
    std::uint32_t arraySize, std::uint32_t arraySlice,
    std::uint32_t sampleCount) noexcept {
    if (!width || !height || !mipLevels || mip >= mipLevels ||
        mip >= 32u || !arraySize || arraySlice >= arraySize ||
        !sampleCount || sampleCount > 32u ||
        (sampleCount != 1u && (mip != 0u || mipLevels != 1u)))
        return {};
    const auto w = width >> mip;
    const auto h = height >> mip;
    return {w ? w : 1u, h ? h : 1u, true};
}
[[nodiscard]] constexpr NativeGamePostpassMipExtent
native_game_postpass_source_box(
    std::uint32_t width, std::uint32_t height,
    std::uint32_t mipLevels, std::uint32_t mip,
    std::uint32_t arraySize, std::uint32_t arraySlice,
    std::uint32_t sampleCount,
    std::uint32_t left, std::uint32_t top,
    std::uint32_t right, std::uint32_t bottom) noexcept {
    const auto extent = native_game_postpass_mip_extent(
        width, height, mipLevels, mip, arraySize, arraySlice, sampleCount);
    if (!extent.valid || left >= right || top >= bottom ||
        right > extent.width || bottom > extent.height) return {};
    return extent;
}
} // namespace outrun::vr::dx11
