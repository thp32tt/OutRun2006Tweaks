#pragma once
#include <cmath>

namespace outrun::vr::dx11::live_game_frame {

// D3D9 samples at integer window pixel centers and D3D11 at half integers.
// Shift the real game's XYZRHW or World/View/Projection clip position by
// +0.5 pixels in X/Y, as a homogeneous offset (no division by W).
// D3D11 viewport maps positive clip Y upwards, hence the negative Y sign.
// Negative-W and W=0 geometry retain hardware clipping semantics.
// Return false transactionally when invalid; original D3D9 always renders.
inline bool game_native_d3d9_raster_center(
    float (&clip)[4], float viewportWidth, float viewportHeight) noexcept {
    if (!std::isfinite(viewportWidth) || !std::isfinite(viewportHeight) ||
        viewportWidth <= 0.0f || viewportHeight <= 0.0f ||
        !std::isfinite(clip[0]) || !std::isfinite(clip[1]) ||
        !std::isfinite(clip[2]) || !std::isfinite(clip[3]))
        return false;
    const float x = clip[0] + clip[3] / viewportWidth;
    const float y = clip[1] - clip[3] / viewportHeight;
    if (!std::isfinite(x) || !std::isfinite(y)) return false;
    clip[0] = x;
    clip[1] = y;
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
