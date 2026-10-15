#pragma once

// R19's fallback has one allocation extent for two array-swapchain slices.
// Respect both incoming stereo rectangles instead of using only the left eye.
#include <algorithm>
#include <cstdint>

namespace OutRunVrFallbackProjectionExtent
{
    struct Size
    {
        std::uint32_t width{};
        std::uint32_t height{};
        constexpr bool Valid() const noexcept { return width != 0 && height != 0; }
    };

    constexpr Size Resolve(std::int32_t leftWidth, std::int32_t leftHeight,
        std::int32_t rightWidth, std::int32_t rightHeight) noexcept
    {
        // Invalid signed OpenXR sizes are not valid RT dimensions.
        if (leftWidth <= 0 || leftHeight <= 0 ||
            rightWidth <= 0 || rightHeight <= 0)
            return {};
        const auto width = std::max(leftWidth, rightWidth);
        const auto height = std::max(leftHeight, rightHeight);
        // Match the bounded per-eye DX9Ex allocation policy.
        if (width > 8192 || height > 8192)
            return {};
        return {static_cast<std::uint32_t>(width),
                static_cast<std::uint32_t>(height)};
    }
}
