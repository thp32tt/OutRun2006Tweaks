#pragma once
#include <cstddef>
#include <cstdint>

// Portable policy for live game-authored D3D9 source textures. The numeric
// constants are checked against the Windows SDK in live_game_frame_bridge.cpp.
// DEFAULT DYNAMIC is lockable; ordinary DEFAULT is NOT. DEFAULT render-target
// textures use an entirely separate GetRenderTargetData staging readback.
namespace outrun::vr::dx11::live_game_frame::dynamic_texture {
enum class SourceRoute : std::uint8_t {
    unsupported, cpu_lockable, dynamic_default, render_target_readback
};
constexpr unsigned kDefaultPool = 0u;
constexpr unsigned kDynamicUsage = 0x00000200u;
constexpr SourceRoute source_route(unsigned pool, unsigned usage,
                                   bool supportedRenderTarget) noexcept {
    if (pool != kDefaultPool) return SourceRoute::cpu_lockable;
    if (supportedRenderTarget) return SourceRoute::render_target_readback;
    return usage == kDynamicUsage ? SourceRoute::dynamic_default :
                                    SourceRoute::unsupported;
}
constexpr bool readable_pitch(std::int64_t pitch, std::size_t rowBytes) noexcept {
    return pitch > 0 && rowBytes > 0 &&
        static_cast<std::uint64_t>(pitch) >= rowBytes;
}
} // namespace outrun::vr::dx11::live_game_frame::dynamic_texture
