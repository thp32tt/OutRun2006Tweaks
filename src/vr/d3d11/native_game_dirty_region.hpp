#pragma once
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// D3D9 Present may supply an explicit dirty RGNDATA despite repainting the
// entire backbuffer. One verified full-surface rectangle permits native
// menu/vehicle/race output; partial or malformed regions stay D3D9-owned.
struct GameNativeDirtyRegionCoverage {
    [[nodiscard]] static constexpr bool covers_full_backbuffer(
        std::uint32_t width, std::uint32_t height,
        std::uint32_t rectangleCount, std::uint32_t bufferBytes,
        std::int64_t boundLeft, std::int64_t boundTop,
        std::int64_t boundRight, std::int64_t boundBottom,
        std::int64_t rectLeft, std::int64_t rectTop,
        std::int64_t rectRight, std::int64_t rectBottom) noexcept {
        return width != 0u && height != 0u &&
            width <= static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)()) &&
            height <= static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)()) &&
            rectangleCount == 1u && bufferBytes >= 16u &&
            boundLeft == 0 && boundTop == 0 &&
            boundRight == static_cast<std::int64_t>(width) &&
            boundBottom == static_cast<std::int64_t>(height) &&
            rectLeft == boundLeft && rectTop == boundTop &&
            rectRight == boundRight && rectBottom == boundBottom;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
