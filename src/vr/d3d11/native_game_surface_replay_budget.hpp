#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Limit expensive diagnostic CPU/GDI/StretchRect compatibility snapshots by
// the full source bytes synchronized from the REAL D3D9 backbuffer. A fixed
// eight-operation cap used to truncate 1080p menu/vehicle overlay bursts,
// while charging only dirty rectangles would undercount GetRenderTargetData.
// Never changes original D3D9 rendering, Present, gamepad or FFB.
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
    [[nodiscard]] constexpr bool admits(
        std::uint32_t width, std::uint32_t height) const noexcept {
        const auto cost = full_readback_bytes(width, height);
        return cost != 0u && operations < kMaxOperations &&
            bytes <= kMaxBytes && cost <= kMaxBytes - bytes;
    }
    // Call only AFTER the original surface snapshot and native staging/copy
    // succeed. Never charge a rejected D3D9 source or an HMD/CI-only probe.
    void note_success(std::uint32_t width, std::uint32_t height) noexcept {
        if (!admits(width, height)) return;
        bytes += full_readback_bytes(width, height);
        ++operations;
    }
    void reset() noexcept { bytes = 0u; operations = 0u; }
};
} // namespace outrun::vr::dx11::live_game_frame
