#pragma once
// Game-created D3D9 fixed-function viewport depth -> native D3D11 clip depth.
// A native diagnostic Draw has a [0,1] D3D11 viewport. D3D9's object-space
// clip coordinates are still upstream of its MinZ/MaxZ viewport depth map.
// XYZRHW game vertices instead already carry post-viewport window depth.
#include <array>
#include <cmath>

namespace outrun::vr::dx11::live_game_frame {
inline bool game_native_viewport_depth_valid(float minZ, float maxZ) noexcept {
    // Equal and reversed bounds are meaningful D3D9 depth viewport modes.
    return std::isfinite(minZ) && std::isfinite(maxZ) &&
           minZ >= 0.0f && minZ <= 1.0f &&
           maxZ >= 0.0f && maxZ <= 1.0f;
}

inline bool game_native_world_depth_clip(std::array<float, 4>& clip,
                                         float minZ, float maxZ) noexcept {
    if (!game_native_viewport_depth_valid(minZ, maxZ) ||
        !std::isfinite(clip[2]) || !std::isfinite(clip[3]))
        return false;
    // Preserve homogeneous coordinates (including signed W for near-camera
    // GPU clipping), while reproducing the D3D9 Z viewport transform.
    const float remapped = (maxZ - minZ) * clip[2] + minZ * clip[3];
    if (!std::isfinite(remapped)) return false;
    clip[2] = remapped;
    return true;
}

inline bool game_native_screen_depth_clip(float windowZ, float w,
                                          float minZ, float maxZ,
                                          float& clipZ) noexcept {
    if (!game_native_viewport_depth_valid(minZ, maxZ) ||
        !std::isfinite(windowZ) || !std::isfinite(w) || w <= 0.0f)
        return false;
    // Pretransformed XYZRHW z is already the D3D9 window-space depth.
    // Applying MinZ/MaxZ again would double-transform menu/HUD sprites.
    const float remapped = windowZ * w;
    if (!std::isfinite(remapped)) return false;
    clipZ = remapped;
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
