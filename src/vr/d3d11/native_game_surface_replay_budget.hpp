#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Budget synchronized real D3D9 source bytes. A pre-Draw seed or failed
// GPU tile capture reads the entire original backbuffer; only a successful
// cropped D3D9 RT->RT copy + GetRenderTargetData reads the tile extent.
// The independent per-frame operation ceiling prevents unbounded bursts.
// Never change original game Draw/Present/input/FFB on admission failure.
struct GameNativeSurfaceReplayBudget {
    static constexpr std::uint64_t kMaxBytes = 256ull * 1024ull * 1024ull;
    static constexpr std::uint64_t kMaxPixels = 16ull * 1024ull * 1024ull;
    static constexpr std::uint32_t kMaxOperations = 64u;
    std::uint32_t operations = 0u;
    std::uint64_t bytes = 0u;
    [[nodiscard]] static constexpr std::uint64_t full_readback_bytes(
        std::uint32_t width, std::uint32_t height) noexcept {
        const auto pixels = std::uint64_t(width) * height;
        return width && height && pixels <= kMaxPixels ? pixels * 4u : 0u;
    }
    // Charge exactly one authenticated D3D9 GPU->CPU readback, never the
    // destination rect size of a fallback full-source GetRenderTargetData.
    [[nodiscard]] constexpr bool admits_bytes(std::uint64_t cost) const noexcept {
        return cost != 0u && operations < kMaxOperations &&
            bytes <= kMaxBytes && cost <= kMaxBytes - bytes;
    }
    [[nodiscard]] constexpr bool admits(
        std::uint32_t width, std::uint32_t height) const noexcept {
        return admits_bytes(full_readback_bytes(width,height));
    }
    void note_success_bytes(std::uint64_t cost) noexcept {
        if (!admits_bytes(cost)) return;
        bytes += cost;
        ++operations;
    }
    // Full-surface API remains the only path for pre-Draw and driver fallback.
    void note_success(std::uint32_t width, std::uint32_t height) noexcept {
        note_success_bytes(full_readback_bytes(width,height));
    }
    void reset() noexcept { bytes=0u; operations=0u; }
};
} // namespace outrun::vr::dx11::live_game_frame
