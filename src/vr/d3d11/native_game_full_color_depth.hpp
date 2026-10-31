#pragma once
namespace outrun::vr::dx11::live_game_frame {
// A full-screen color+Z Clear is safe to mirror only when its actual D3D9
// depth buffer and value can seed the subsequent game-created native Draw.
// Stencil is not represented by this native fixed-function subset.
struct GameNativeFullColorDepthClear {
    [[nodiscard]] static constexpr bool can_mirror(
        bool depthCleared, bool stencilCleared, bool depthCompatible, float z) noexcept {
        return depthCleared && !stencilCleared && depthCompatible &&
            z >= 0.0f && z <= 1.0f;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
