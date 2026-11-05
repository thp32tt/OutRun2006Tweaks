#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// Source surface and primary Present backbuffer carry canonical IUnknown IDs.
// Same D3D9 device is insufficient: offscreen menu/race RT draws are not
// presentable backbuffer draws even if dimensions match.
struct GameNativeBackbufferAdmission {
    std::uintptr_t targetIdentity = 0, backbufferIdentity = 0;
    std::uint32_t targetWidth = 0, targetHeight = 0;
    std::uint32_t backbufferWidth = 0, backbufferHeight = 0;
    std::uint32_t viewportX = 0, viewportY = 0;
    std::uint32_t viewportWidth = 0, viewportHeight = 0;
    bool formatMatches = false, supportedBackbufferFormat = false;
    bool singleSample = false;
    [[nodiscard]] constexpr bool accepts(std::uint32_t insetWidth,
                                         std::uint32_t insetHeight,
                                         std::uint32_t margin) const noexcept {
        return targetIdentity != 0 && targetIdentity == backbufferIdentity &&
            targetWidth != 0 && targetHeight != 0 &&
            targetWidth == backbufferWidth && targetHeight == backbufferHeight &&
            formatMatches && supportedBackbufferFormat && singleSample &&
            viewportWidth != 0 && viewportHeight != 0 &&
            viewportX <= backbufferWidth && viewportY <= backbufferHeight &&
            viewportWidth <= backbufferWidth - viewportX &&
            viewportHeight <= backbufferHeight - viewportY &&
            margin <= backbufferWidth && margin <= backbufferHeight &&
            insetWidth <= backbufferWidth - margin &&
            insetHeight <= backbufferHeight - margin;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
