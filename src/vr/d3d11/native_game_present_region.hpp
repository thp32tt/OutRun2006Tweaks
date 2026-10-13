#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// D3D9 Present's source rectangle is measured in backbuffer pixels.
// A native inset outside that crop is not visible even if UpdateSurface worked.
struct GameNativePresentRegion {
    std::int64_t left = 0, top = 0, right = 0, bottom = 0;
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
