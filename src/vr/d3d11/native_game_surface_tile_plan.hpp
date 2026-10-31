#pragma once
#include <cstdint>
#include "native_game_surface_copy_region.hpp"

namespace outrun::vr::dx11::live_game_frame {
// Transfer EXACT original post-Draw backbuffer rectangle to CPU staging.
// Pre-Draw first-native-Draw seeds remain complete-source readbacks.
struct GameNativeSurfaceTilePlan {
    [[nodiscard]] static constexpr bool eligible(
        GameNativeSurfaceCopyRegion r,
        std::uint32_t fullWidth, std::uint32_t fullHeight) noexcept {
        return r.valid && fullWidth && fullHeight &&
            r.left < r.right && r.top < r.bottom &&
            r.right <= fullWidth && r.bottom <= fullHeight &&
            (r.left != 0u || r.top != 0u ||
             r.right != fullWidth || r.bottom != fullHeight);
    }
    [[nodiscard]] static constexpr std::uint32_t source_x(
        GameNativeSurfaceCopyRegion r, bool tileSucceeded) noexcept {
        return tileSucceeded ? 0u : r.left;
    }
    [[nodiscard]] static constexpr std::uint32_t source_y(
        GameNativeSurfaceCopyRegion r, bool tileSucceeded) noexcept {
        return tileSucceeded ? 0u : r.top;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
