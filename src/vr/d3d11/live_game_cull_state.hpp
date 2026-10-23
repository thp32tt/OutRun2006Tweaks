#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
struct GameNativeCullAdmission {
    std::uint32_t d3d9Mode = 1u;
};
// D3D9 NONE=1,CW=2,CCW=3: CullMode describes discarded screen winding.
// Native BACK with FrontCounterClockwise=TRUE discards CW, FALSE discards CCW.
// Point and line calls ignore triangle cull, preserving native no-cull raster.
constexpr bool game_native_cull_admission(
    std::uint32_t mode, std::uint32_t primitive,
    GameNativeCullAdmission& result) noexcept {
    if (mode < 1u || mode > 3u || primitive < 1u || primitive > 6u) return false;
    result.d3d9Mode = primitive >= 4u ? mode : 1u;
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
