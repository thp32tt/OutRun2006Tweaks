#pragma once
#include "native_game_present_region.hpp"
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// D3D9 Present can expose one dirty sub-rectangle rather than a full repaint.
// Only copy the intersection with its visible source crop; all other game
// backbuffer pixels and the original D3D9/input fallback remain authoritative.
struct GameNativePartialDirtySelection {
    GameNativePresentRegion source{};
    bool valid = false;
};
struct GameNativePartialDirtyUpload {
    [[nodiscard]] static constexpr GameNativePartialDirtySelection select(
        std::uint32_t width, std::uint32_t height,
        GameNativePresentRegion presentSource,
        std::uint32_t rectangleCount, std::uint32_t bufferBytes,
        std::int64_t boundLeft, std::int64_t boundTop,
        std::int64_t boundRight, std::int64_t boundBottom,
        std::int64_t rectLeft, std::int64_t rectTop,
        std::int64_t rectRight, std::int64_t rectBottom) noexcept {
        if (!presentSource.full_frame_placement(width, height, width, height).valid ||
            rectangleCount != 1u || bufferBytes < 16u ||
            rectLeft < 0 || rectTop < 0 || rectRight <= rectLeft ||
            rectBottom <= rectTop ||
            rectRight > static_cast<std::int64_t>(width) ||
            rectBottom > static_cast<std::int64_t>(height) ||
            boundLeft != rectLeft || boundTop != rectTop ||
            boundRight != rectRight || boundBottom != rectBottom)
            return {};
        const std::int64_t left = rectLeft > presentSource.left ? rectLeft : presentSource.left;
        const std::int64_t top = rectTop > presentSource.top ? rectTop : presentSource.top;
        const std::int64_t right = rectRight < presentSource.right ? rectRight : presentSource.right;
        const std::int64_t bottom = rectBottom < presentSource.bottom ? rectBottom : presentSource.bottom;
        if (left >= right || top >= bottom) return {};
        return {{left, top, right, bottom}, true};
    }
};
} // namespace outrun::vr::dx11::live_game_frame
