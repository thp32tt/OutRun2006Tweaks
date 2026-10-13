#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// D3D9 Present's source rectangle is measured in backbuffer pixels.
// A native inset outside that crop is not visible even if UpdateSurface worked.
struct GameNativeInsetPlacement {
    std::uint32_t left = 0, top = 0;
    bool valid = false;
};

struct GameNativePresentRegion {
    std::int64_t left = 0, top = 0, right = 0, bottom = 0;
    // Preserve the inset for menu/car/race Present source crops, including
    // crops that omit the backbuffer's original top-right corner. Origin is
    // expressed in D3D9 backbuffer coordinates, not cropped destination pixels.
    [[nodiscard]] constexpr GameNativeInsetPlacement inset_placement(
        std::uint32_t backbufferWidth, std::uint32_t backbufferHeight,
        std::uint32_t insetWidth, std::uint32_t insetHeight,
        std::uint32_t margin) const noexcept {
        // POINT uses signed 32-bit LONG. All additions use signed 64-bit
        // so pathological crop/margin sizes fail closed, never wrap.
        if (!backbufferWidth || !backbufferHeight || !insetWidth || !insetHeight ||
            backbufferWidth > 0x7fffffffU || backbufferHeight > 0x7fffffffU ||
            left < 0 || top < 0 || right <= left || bottom <= top ||
            right > static_cast<std::int64_t>(backbufferWidth) ||
            bottom > static_cast<std::int64_t>(backbufferHeight) ||
            right - left < static_cast<std::int64_t>(insetWidth) + 2LL * margin ||
            bottom - top < static_cast<std::int64_t>(insetHeight) + 2LL * margin)
            return {};
        return {static_cast<std::uint32_t>(right - margin - insetWidth),
                static_cast<std::uint32_t>(top + margin), true};
    }
    [[nodiscard]] constexpr bool allows_inset(
        std::uint32_t backbufferWidth, std::uint32_t backbufferHeight,
        std::uint32_t insetWidth, std::uint32_t insetHeight,
        std::uint32_t margin) const noexcept {
        if (!backbufferWidth || !backbufferHeight || !insetWidth || !insetHeight ||
            insetWidth > backbufferWidth || insetHeight > backbufferHeight ||
            margin > backbufferWidth - insetWidth ||
            margin > backbufferHeight - insetHeight ||
            left < 0 || top < 0 || right <= left || bottom <= top ||
            right > static_cast<std::int64_t>(backbufferWidth) ||
            bottom > static_cast<std::int64_t>(backbufferHeight)) return false;
        // Original UpdateSurface places the diagnostic frame top-right.
        const std::int64_t insetLeft = backbufferWidth - insetWidth - margin;
        const std::int64_t insetTop = margin;
        return left <= insetLeft && top <= insetTop &&
            right >= insetLeft + insetWidth &&
            bottom >= insetTop + insetHeight;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
