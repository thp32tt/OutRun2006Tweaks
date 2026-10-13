#pragma once
#include <array>
#include <cmath>

namespace outrun::vr::dx11::live_game_frame {

// D3D9 object-space World*View*Projection produces homogeneous clip coordinates.
// D3D11 clips edges against its clip volume *before* dividing by W, so a
// negative-W vertex may belong to a visible triangle crossing the near plane.
// Never perspective-divide on the CPU or reject the entire live Draw for W<0.
// Invalid/zero-W vertices still use the original D3D9 rendering path.
inline bool game_native_object_clip_position(
    const std::array<float, 4>& clip) noexcept {
    return std::isfinite(clip[0]) && std::isfinite(clip[1]) &&
           std::isfinite(clip[2]) && std::isfinite(clip[3]) &&
           clip[3] != 0.0f;
}

} // namespace outrun::vr::dx11::live_game_frame
