#pragma once
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// D3D9 Present may supply an explicit dirty RGNDATA despite repainting the
// entire backbuffer. One verified full-surface rectangle permits native
// menu/vehicle/race output; partial or malformed regions stay D3D9-owned.
struct GameNativeDirtyRectangle {
    std::int64_t left = 0, top = 0, right = 0, bottom = 0;
};
struct GameNativeDirtyRegionCoverage {
    static constexpr std::uint32_t kMaxPartitionRects = 8u;
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

    // An exact dirty RECT that fills the *visible* Present source crop is
    // safe for a bounded source-only UpdateSurface. Do not overwrite pixels
    // outside that crop: later menu/car/race partial Presents may reuse them.
    // A whole-backbuffer region stays on covers_full_backbuffer() instead.
    [[nodiscard]] static constexpr bool covers_present_crop(
        std::uint32_t width, std::uint32_t height,
        std::uint32_t rectangleCount, std::uint32_t bufferBytes,
        std::int64_t cropLeft, std::int64_t cropTop,
        std::int64_t cropRight, std::int64_t cropBottom,
        std::int64_t boundLeft, std::int64_t boundTop,
        std::int64_t boundRight, std::int64_t boundBottom,
        std::int64_t rectLeft, std::int64_t rectTop,
        std::int64_t rectRight, std::int64_t rectBottom) noexcept {
        if (!width || !height ||
            width > static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)()) ||
            height > static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)()) ||
            rectangleCount != 1u || bufferBytes < 16u ||
            cropLeft < 0 || cropTop < 0 ||
            cropRight <= cropLeft || cropBottom <= cropTop ||
            cropRight > static_cast<std::int64_t>(width) ||
            cropBottom > static_cast<std::int64_t>(height) ||
            (cropLeft == 0 && cropTop == 0 &&
             cropRight == static_cast<std::int64_t>(width) &&
             cropBottom == static_cast<std::int64_t>(height)))
            return false;
        return boundLeft == cropLeft && boundTop == cropTop &&
            boundRight == cropRight && boundBottom == cropBottom &&
            rectLeft == cropLeft && rectTop == cropTop &&
            rectRight == cropRight && rectBottom == cropBottom;
    }
    // Multiple disjoint D3D9 dirty RECTs may describe the entire game frame.
    // The exact union must cover every pixel before native full-frame publication;
    // rcBound alone never proves it (gaps/overlaps retain D3D9 and gamepad).
    [[nodiscard]] static constexpr bool covers_partition(
        std::uint32_t width, std::uint32_t height,
        std::uint32_t rectangleCount, std::uint32_t bufferBytes,
        std::int64_t boundLeft, std::int64_t boundTop,
        std::int64_t boundRight, std::int64_t boundBottom,
        const GameNativeDirtyRectangle* rectangles) noexcept {
        if (!rectangles || !width || !height ||
            width > static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)()) ||
            height > static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)()) ||
            rectangleCount < 2u || rectangleCount > kMaxPartitionRects ||
            bufferBytes < rectangleCount * 16u ||
            boundLeft != 0 || boundTop != 0 ||
            boundRight != static_cast<std::int64_t>(width) ||
            boundBottom != static_cast<std::int64_t>(height)) return false;
        const std::uint64_t total = static_cast<std::uint64_t>(width) * height;
        std::uint64_t covered = 0u;
        for (std::uint32_t i = 0u; i < rectangleCount; ++i) {
            const auto& r = rectangles[i];
            if (r.left < 0 || r.top < 0 || r.right <= r.left ||
                r.bottom <= r.top || r.right > boundRight ||
                r.bottom > boundBottom) return false;
            const std::uint64_t area = static_cast<std::uint64_t>(r.right - r.left) *
                                       static_cast<std::uint64_t>(r.bottom - r.top);
            if (area > total - covered) return false;
            for (std::uint32_t j = 0u; j < i; ++j) {
                const auto& p = rectangles[j];
                if (r.left < p.right && p.left < r.right &&
                    r.top < p.bottom && p.top < r.bottom) return false;
            }
            covered += area;
        }
        return covered == total;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
