#pragma once
// Native eye geometry is produced by a real D3D9Ex game backbuffer, not by
// stretching a desktop-resolution screenshot into the OpenXR swapchain.
// Keep the original game aspect to avoid changing HUD, culling and viewport
// semantics. Every source dimension is >= the runtime's allocated eye size.
// This is an opt-in first stage; auto Reset is deliberately out of scope until
// same-device loss/ownership and gameplay HUD are verified with a headset.
#include <algorithm>
#include <cstdint>
#include <limits>
#include "vr/ipc/xr_eye_extent.hpp"
namespace OutRunVR::EyeExtent
{
    struct NativeBackbuffer
    {
        Size dimensions{};
        bool changed = false;
    };
    inline NativeBackbuffer ResolveNativeBackbuffer(Size game, Size xrEye,
        Size caps, bool windowed, std::uint64_t maxSourcePixels = 16'000'000u) noexcept
    {
        if (!windowed || !Valid(game) || !Valid(xrEye) || !Valid(caps) ||
            !Valid(ResolveGame(xrEye,caps)) ||
            game.width > caps.width || game.height > caps.height)
            return {};
        // Cross-multiplication with uint64 avoids overflow and preserves the
        // game aspect (within rounding of one pixel), even for large surfaces.
        const std::uint64_t minScaleNumerator = std::max(
            static_cast<std::uint64_t>(xrEye.width) * game.height,
            static_cast<std::uint64_t>(xrEye.height) * game.width);
        const std::uint64_t minScaleDenominator =
            static_cast<std::uint64_t>(game.width) * game.height;
        if (!minScaleDenominator) return {};
        // Height is the optimization dimension for today's ~3440x1440 desktop
        // and ~2124x2284 XR target, but also handle eye widths that dominate.
        const std::uint64_t height = std::max<std::uint64_t>(game.height,
            (minScaleNumerator + game.width - 1) / game.width);
        const std::uint64_t width = std::max<std::uint64_t>(game.width,
            (static_cast<std::uint64_t>(game.width) * height + game.height - 1) / game.height);
        if (!height || !width || width > caps.width || height > caps.height ||
            width > 8192 || height > 8192 || width * height > maxSourcePixels ||
            width < xrEye.width || height < xrEye.height)
            return {};
        Size result{static_cast<std::uint32_t>(width),static_cast<std::uint32_t>(height)};
        return {result,!Equal(game,result)};
    }
}
