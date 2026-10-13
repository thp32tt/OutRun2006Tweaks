#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Diagnostic compositing only; original D3D9 Draw/Present/input remain intact.
struct GameNativeFrameBatch {
    static constexpr std::uint32_t kMaxDraws = 8u;
    std::uint32_t submitted = 0u;
    bool stopped = false;
    bool depthReady = false;
    constexpr bool accepts(std::uint32_t ordinal, std::uint32_t slot,
                           bool multi) const noexcept {
        if (stopped) return false;
        if (!multi) return submitted == 0u && ordinal == slot;
        return submitted < kMaxDraws && ordinal >= slot;
    }
    constexpr bool first_draw() const noexcept { return submitted == 0u; }
    constexpr bool clear_depth() const noexcept { return !depthReady; }
    constexpr void succeeded(bool depth) noexcept {
        ++submitted; if (depth) depthReady = true;
    }
    constexpr void abort() noexcept { stopped = true; }
    constexpr void reset() noexcept {
        submitted = 0u; stopped = false; depthReady = false;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
