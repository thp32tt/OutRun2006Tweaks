#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
struct GameNativeDepthAdmission {
    bool enabled = false;
    bool lessEqual = false;
    bool writeEnabled = false;
    bool always = false; // D3DCMP_ALWAYS does not suppress Z writes.
    std::uint32_t equalityMode = 0u; // D3DCMP_EQUAL=3 or D3DCMP_NOTEQUAL=6.
};
// D3D9 D3DZB_FALSE=0, D3DZB_TRUE=1, D3DZB_USEW=2.
// D3DCMP_LESS=2, EQUAL=3, LESSEQUAL=4, NOTEQUAL=6, ALWAYS=8. No Windows dependency.
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
        (zFunc != 2u && zFunc != 4u && zFunc != 8u &&
         zFunc != 3u && zFunc != 6u) ||
        (depthBiasBits & 0x7fffffffu) != 0u ||
        (slopeBiasBits & 0x7fffffffu) != 0u ||
        !validDepthSurface) return false;
    output = {true, zFunc == 4u, zWrite == 1u};
    output.always = zFunc == 8u;
    output.equalityMode = (zFunc == 3u || zFunc == 6u) ? zFunc : 0u;
    return true;
}
// Four independent OM states: write-off LESS, write-off LEQUAL,
// write-on LESS, write-on LEQUAL. Both creation AND binding must select
// the exact same slot; a missing +2 silently binds an uninitialized state.
constexpr std::uint32_t game_native_depth_slot(
    bool writeEnabled, bool lessEqual) noexcept {
    return (writeEnabled ? 2u : 0u) + (lessEqual ? 1u : 0u);
}
// Separate EQUAL/NOTEQUAL x Z-write slots. The admission caller guarantees
// equalityMode is 3 or 6; invalid comparisons never reach a native draw.
constexpr std::uint32_t game_native_depth_equality_slot(
    bool writeEnabled, std::uint32_t equalityMode) noexcept {
    return (writeEnabled ? 2u : 0u) + (equalityMode == 6u ? 1u : 0u);
}
} // namespace outrun::vr::dx11::live_game_frame
