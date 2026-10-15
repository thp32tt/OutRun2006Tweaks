#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// A real game Draw can write zero pixels when its enabled D3D9 scissor
// is entirely disjoint from the viewport. Valid disjoint rectangles preserve
// Draw/DrawIndexed source ordering without a fake D3D11 draw submission.
struct GameNativeScissorClip {
    [[nodiscard]] static constexpr bool excludes_viewport(
        std::uint32_t viewportX, std::uint32_t viewportY,
        std::uint32_t viewportWidth, std::uint32_t viewportHeight,
        std::int64_t scissorLeft, std::int64_t scissorTop,
        std::int64_t scissorRight, std::int64_t scissorBottom) noexcept {
        if (viewportWidth == 0u || viewportHeight == 0u ||
            scissorRight <= scissorLeft || scissorBottom <= scissorTop)
            return false; // malformed/unknown: ordinary D3D9 fallback
        const std::int64_t viewportRight =
            static_cast<std::int64_t>(viewportX) + viewportWidth;
        const std::int64_t viewportBottom =
            static_cast<std::int64_t>(viewportY) + viewportHeight;
        return scissorRight <= static_cast<std::int64_t>(viewportX) ||
            scissorLeft >= viewportRight ||
            scissorBottom <= static_cast<std::int64_t>(viewportY) ||
            scissorTop >= viewportBottom;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
