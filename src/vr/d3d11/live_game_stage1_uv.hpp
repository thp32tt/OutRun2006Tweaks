#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// Only game-provided FVF texture coordinates and the native-supported 2D
// fixed-function transform are admissible. D3DTSS_TCI_* generation,
// D3DTTFF_PROJECTED, COUNT1/3/4, and absent FVF slots retain D3D9 Draw.
constexpr bool stage1_game_uv_supported(std::uint32_t coordIndex,
                                       std::uint32_t fvfTexcoordCount,
                                       std::uint32_t transformFlags) noexcept {
    return coordIndex < 8u && coordIndex < fvfTexcoordCount &&
           (transformFlags == 0u || transformFlags == 2u);
}
static_assert(stage1_game_uv_supported(1u, 2u, 0u));
static_assert(stage1_game_uv_supported(0u, 1u, 2u));
static_assert(!stage1_game_uv_supported(1u, 1u, 0u));
static_assert(!stage1_game_uv_supported(0x10000u, 2u, 0u));
static_assert(!stage1_game_uv_supported(1u, 2u, 0x102u));
static_assert(!stage1_game_uv_supported(1u, 2u, 3u));
} // namespace outrun::vr::dx11::live_game_frame
