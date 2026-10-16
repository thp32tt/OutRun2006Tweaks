#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace OutRunVrNativeXrSwapchain
{
    // Production OpenXR xrWaitSwapchainImage -> native L/R projection,
    // world-locked menu and mono theater. Validate before RTV indexing.
    template <typename View>
    [[nodiscard]] bool ImageViewsReady(
        std::uint32_t image, std::size_t declaredImageCount,
        std::uint32_t arraySize,
        const std::vector<std::array<View, 2>>& targets,
        std::uint32_t requestedViews) noexcept
    {
        if (!declaredImageCount || image >= declaredImageCount ||
            image >= targets.size() || requestedViews == 0u ||
            requestedViews > 2u || requestedViews > arraySize)
            return false;
        for (std::uint32_t view = 0; view < requestedViews; ++view)
            if (!targets[image][view])
                return false;
        return true;
    }
}
