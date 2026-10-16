#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
struct GameNativeGpuHandoff {
    // Disallow partial game Draw coverage, foreign/cropped output, unbound
    // producer source, zero generation and inset-only diagnostic frames.
    [[nodiscard]] static constexpr bool may_offer(
        bool full, bool complete, bool writable, bool sameOwner,
        bool gpuReady, bool registered, std::uint32_t width,
        std::uint32_t height, std::uint32_t generation) noexcept {
        return full && complete && writable && sameOwner &&
            gpuReady && registered && width && height && generation;
    }
};
static_assert(GameNativeGpuHandoff::may_offer(
    true,true,true,true,true,true,1920,1080,1));
static_assert(!GameNativeGpuHandoff::may_offer(
    false,true,true,true,true,true,256,144,1));
} // namespace outrun::vr::dx11::live_game_frame
