#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
struct GameNativeDepthAdmission {
    bool enabled = false;
    bool lessEqual = false;
    bool writeEnabled = false;
};
// D3D9 D3DZB_FALSE=0, D3DZB_TRUE=1, D3DZB_USEW=2.
// D3DCMP_LESS=2, D3DCMP_LESSEQUAL=4. No Windows dependency.
// ZWRITEENABLE=FALSE still performs the depth comparison; it only disables
// depth-buffer updates. Keep this state distinct through the native OM bind.
constexpr bool game_native_depth_admission(
    std::uint32_t zEnable, std::uint32_t zWrite, std::uint32_t zFunc,
    std::uint32_t depthBiasBits, std::uint32_t slopeBiasBits,
    bool validDepthSurface, GameNativeDepthAdmission& output) noexcept {
    if (zEnable == 0u) {
        output = {};
        return true;
    }
    // This independent D3D11 DSV reproduces the single Draw's depth state,
    // not previous frame/earlier-game depth contents. Unsupported cases
    // stay in the unmodified, original D3D9 rendering path.
    if (zEnable != 1u || zWrite > 1u ||
        (zFunc != 2u && zFunc != 4u) ||
        (depthBiasBits & 0x7fffffffu) != 0u ||
        (slopeBiasBits & 0x7fffffffu) != 0u ||
        !validDepthSurface) return false;
    output = {true, zFunc == 4u, zWrite == 1u};
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
