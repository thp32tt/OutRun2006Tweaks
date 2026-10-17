#pragma once
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// The region is taken from the ORIGINAL successful D3D9 operation, never
// inferred from a native texture or the Present dirty-region bounding box.
// The consumer copies precisely these destination pixels into the native RTV.
struct GameNativeSurfaceCopyRegion {
    std::uint32_t left{}, top{}, right{}, bottom{};
    bool valid{};
    [[nodiscard]] constexpr std::uint32_t width() const noexcept { return right - left; }
    [[nodiscard]] constexpr std::uint32_t height() const noexcept { return bottom - top; }

    [[nodiscard]] static constexpr GameNativeSurfaceCopyRegion destination(
        std::int64_t left, std::int64_t top, std::int64_t right,
        std::int64_t bottom, std::uint32_t width, std::uint32_t height) noexcept {
        if (!width || !height || width > 0x7fffffffu || height > 0x7fffffffu ||
            left < 0 || top < 0 || right <= left || bottom <= top ||
            right > width || bottom > height) return {};
        const auto w = static_cast<std::uint64_t>(right-left);
        const auto h = static_cast<std::uint64_t>(bottom-top);
        // A single diagnostic CPU->GPU postpass must not allocate unbounded
        // memory on malformed or huge menu/race render-target rectangles.
        if (w*h > 16u*1024u*1024u) return {};
        return {static_cast<std::uint32_t>(left),
                static_cast<std::uint32_t>(top),
                static_cast<std::uint32_t>(right),
                static_cast<std::uint32_t>(bottom), true};
    }

    [[nodiscard]] static constexpr GameNativeSurfaceCopyRegion update_surface(
        std::int64_t srcLeft, std::int64_t srcTop,
        std::int64_t srcRight, std::int64_t srcBottom,
        std::uint32_t sourceWidth, std::uint32_t sourceHeight,
        std::int64_t destX, std::int64_t destY,
        std::uint32_t destWidth, std::uint32_t destHeight) noexcept {
        if (srcLeft < 0 || srcTop < 0 || srcRight <= srcLeft ||
            srcBottom <= srcTop || srcRight > sourceWidth ||
            srcBottom > sourceHeight || destX < 0 || destY < 0)
            return {};
        return destination(destX, destY, destX + (srcRight-srcLeft),
                           destY + (srcBottom-srcTop), destWidth, destHeight);
    }
};
static_assert(GameNativeSurfaceCopyRegion::destination(
    0, 0, 3440, 1440, 3440, 1440).valid);
static_assert(!GameNativeSurfaceCopyRegion::destination(
    -1, 0, 100, 100, 3440, 1440).valid);
static_assert(!GameNativeSurfaceCopyRegion::update_surface(
    0, 0, 500, 500, 500, 500, 3200, 1300, 3440, 1440).valid);
} // namespace outrun::vr::dx11::live_game_frame
