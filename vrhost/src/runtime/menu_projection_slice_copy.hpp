#pragma once
#include <cstdint>

// LOCAL-fixed menu projection uses one clip, UV rectangle and source for
// both eyes. A two-slice, single-mip OpenXR swapchain supports a whole-slice
// GPU copy of the finished left-eye raster instead of redrawing the menu.
// Never use this optimization on world stereo, asymmetric menu clips,
// missing runtime textures or non-two-slice swapchains.
namespace OutRunVrMenuProjectionCopy
{
    constexpr bool CanCopyIdenticalEye(
        bool firstEyeRendered, bool identicalContent,
        std::uint32_t arraySize, bool imageTextureAvailable,
        bool secondRtvAvailable) noexcept
    {
        return firstEyeRendered && identicalContent && arraySize == 2 &&
            imageTextureAvailable && secondRtvAvailable;
    }
}
