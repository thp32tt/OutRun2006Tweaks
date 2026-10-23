#pragma once
#include <array>
#include <cmath>

namespace outrun::vr::dx11::live_game_frame {

// D3D9 object-space World*View*Projection produces homogeneous clip coordinates.
// D3D11 clips edges against its clip volume *before* dividing by W, so a
// negative-W vertex may belong to a visible triangle crossing the near plane.
// Never perspective-divide on the CPU or reject the entire live Draw for W<0.
// Preserve finite camera-plane W=0 edge vertices for GPU homogeneous clipping.
// The fully zero homogeneous vector has no projected direction and falls back
// to the original D3D9 Draw/Present/input instead of invoking undefined rasterization.
inline bool game_native_object_clip_position(
    const std::array<float, 4>& clip) noexcept {
    return std::isfinite(clip[0]) && std::isfinite(clip[1]) &&
           std::isfinite(clip[2]) && std::isfinite(clip[3]) &&
           (clip[3] != 0.0f || clip[0] != 0.0f ||
            clip[1] != 0.0f || clip[2] != 0.0f);
}

} // namespace outrun::vr::dx11::live_game_frame
