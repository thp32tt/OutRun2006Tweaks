#pragma once
#include <array>
#include <cstdint>
#include <limits>
#include "native_game_dirty_region.hpp"
#include "native_game_present_region.hpp"

namespace outrun::vr::dx11::live_game_frame {
// Every game Present publication, including a single full/cropped region,
// preserves its original D3D9 pixels before the first cross-API StretchRect.
// A failed driver blit may have written some pixels even on HRESULT failure.
// Exact tiles avoid copying unrelated HUD pixels between sparse dirty regions.
struct NativeSharedDesktopRollbackPlan {
    struct Tile { std::uint32_t width = 0u, height = 0u; };
    std::array<Tile, GameNativeDirtyRegionCoverage::kMaxPartitionRects> tiles{};
    std::uint32_t count = 0u;
    std::uint64_t totalPixels = 0u;
    bool valid = false;

    [[nodiscard]] static constexpr NativeSharedDesktopRollbackPlan select(
        std::uint32_t width, std::uint32_t height,
        const GameNativePresentRegion* regions,
        std::uint32_t count) noexcept {
        if (!regions || !width || !height || width > 0x7fffffffu ||
            height > 0x7fffffffu || count == 0u ||
            count > GameNativeDirtyRegionCoverage::kMaxPartitionRects)
            return {};
        NativeSharedDesktopRollbackPlan result{};
        for (std::uint32_t i = 0u; i < count; ++i) {
            const auto& r = regions[i];
            if (r.left < 0 || r.top < 0 || r.right <= r.left ||
                r.bottom <= r.top || r.right > width || r.bottom > height)
                return {};
            const auto tileWidth = static_cast<std::uint32_t>(r.right - r.left);
            const auto tileHeight = static_cast<std::uint32_t>(r.bottom - r.top);
            const std::uint64_t pixels =
                static_cast<std::uint64_t>(tileWidth) * tileHeight;
            if (pixels > (std::numeric_limits<std::uint64_t>::max)() -
                result.totalPixels)
                return {};
            result.tiles[i] = {tileWidth, tileHeight};
            result.totalPixels += pixels;
        }
        result.count = count;
        result.valid = true;
        return result;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
