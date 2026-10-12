#pragma once
#include <cstdint>

// Only the consecutive right eye of an uninterrupted, same-extent projection
// pair inherits viewport, shader, topology and sampler state from eye 0.
// Each eye ALWAYS binds its own RTV/SRV/constant buffer and performs a draw.
// Any failed first-eye upload/draw, unexpected ordering, or size mismatch
// falls back to complete D3D11 state setup for the second eye.
namespace OutRunVrProjectionPair
{
    // A consecutive right-eye submission replaces eye 0's RTV/SRV on the
    // same immediate context. Never defer across different eye order/extent;
    // the caller must clean up if the second draw aborts before rebinding.
    constexpr bool CanDeferFirstEyeUnbind(
        int firstEyeIndex, int nextEyeIndex,
        std::uint32_t firstWidth, std::uint32_t firstHeight,
        std::uint32_t nextWidth, std::uint32_t nextHeight) noexcept
    {
        return firstEyeIndex == 0 && nextEyeIndex == 1 &&
            firstWidth != 0 && firstHeight != 0 &&
            firstWidth == nextWidth && firstHeight == nextHeight;
    }
    constexpr bool CanReuseCommonPipeline(
        bool firstEyeSucceeded, int firstEyeIndex, int secondEyeIndex,
        std::uint32_t firstWidth, std::uint32_t firstHeight,
        std::uint32_t secondWidth, std::uint32_t secondHeight) noexcept
    {
        return firstEyeSucceeded && firstEyeIndex == 0 &&
            secondEyeIndex == 1 && firstWidth != 0 && firstHeight != 0 &&
            firstWidth == secondWidth && firstHeight == secondHeight;
    }
    static_assert(CanDeferFirstEyeUnbind(0, 1, 2048, 2160, 2048, 2160));
    static_assert(!CanDeferFirstEyeUnbind(1, 0, 2048, 2160, 2048, 2160));
    static_assert(!CanDeferFirstEyeUnbind(0, 1, 0, 2160, 0, 2160));
    static_assert(!CanDeferFirstEyeUnbind(0, 1, 2048, 2160, 1920, 2160));
    static_assert(CanReuseCommonPipeline(true, 0, 1, 2048, 2160, 2048, 2160));
    static_assert(!CanReuseCommonPipeline(false, 0, 1, 2048, 2160, 2048, 2160));
    static_assert(!CanReuseCommonPipeline(true, 1, 0, 2048, 2160, 2048, 2160));
    static_assert(!CanReuseCommonPipeline(true, 0, 1, 2048, 2160, 1920, 2160));
    static_assert(!CanReuseCommonPipeline(true, 0, 1, 2048, 2160, 2048, 1920));
    static_assert(!CanReuseCommonPipeline(true, 0, 1, 0, 2160, 0, 2160));
}
