#pragma once
#include <cstdint>
#include "native_game_surface_copy_region.hpp"
#include "native_game_surface_replay_budget.hpp"
#include "native_game_surface_tile_plan.hpp"

namespace outrun::vr::dx11::live_game_frame {
// One source-of-truth cost for an ORIGINAL game backbuffer surface mutation.
// A cold/Reset seed and a whole-surface GDI write still read every pixel.
// After a real native Draw, only a valid partial game LockRect may use the
// same cropped D3D9 RT staging route as preserve_game_surface_copy.
// The caller must recheck the FULL cost if a driver rejects the GPU crop.
struct GameNativeCpuTileAdmission {
    [[nodiscard]] static constexpr std::uint64_t planned_bytes(
        GameNativeSurfaceCopyRegion region,
        std::uint32_t fullWidth, std::uint32_t fullHeight,
        bool requireFullSource) noexcept {
        if (!region.valid || !fullWidth || !fullHeight ||
            region.right > fullWidth || region.bottom > fullHeight ||
            region.left >= region.right || region.top >= region.bottom)
            return 0u;
        if (!requireFullSource &&
            GameNativeSurfaceTilePlan::eligible(
                region, fullWidth, fullHeight))
            return GameNativeSurfaceReplayBudget::full_readback_bytes(
                region.width(), region.height());
        return GameNativeSurfaceReplayBudget::full_readback_bytes(
            fullWidth, fullHeight);
    }
};
} // namespace outrun::vr::dx11::live_game_frame
