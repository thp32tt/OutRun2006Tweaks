#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// A D3D9 fragment always rejected by the alpha or Z comparison cannot write
// color, destination alpha or depth. The live caller separately proves a
// cleared game backbuffer, no stencil operations and no additional MRT.
// Consumes only the original source ordinal; NEVER authorizes a native draw.
struct GameNativeFragmentReject {
    static constexpr std::uint32_t kNever = 1u; // D3DCMP_NEVER
    [[nodiscard]] static constexpr bool no_target_write(
        bool fullFrame, bool clearedBackbuffer, bool sameMainTarget,
        bool noExtraTargets, bool stencilDisabled,
        bool alphaTestEnabled, std::uint32_t alphaFunc,
        bool depthTestEnabled, std::uint32_t depthFunc) noexcept {
        return fullFrame && clearedBackbuffer && sameMainTarget &&
            noExtraTargets && stencilDisabled &&
            ((alphaTestEnabled && alphaFunc == kNever) ||
             (depthTestEnabled && depthFunc == kNever));
    }
};
} // namespace outrun::vr::dx11::live_game_frame
