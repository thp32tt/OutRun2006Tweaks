#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Diagnostic compositing only; original D3D9 Draw/Present/input remain intact.
struct GameNativeFrameBatch {
    static constexpr std::uint32_t kMaxDraws = 8u;
    std::uint32_t submitted = 0u;
    bool stopped = false;
    bool depthReady = false;
    // Inset Z accumulation cannot mix forward and reverse D3D9 comparisons.
    std::uint32_t depthDirection = 0u;
    constexpr bool accepts(std::uint32_t ordinal, std::uint32_t slot,
                           bool multi) const noexcept {
        if (stopped) return false;
        if (!multi) return submitted == 0u && ordinal == slot;
        // A batch represents one contiguous slice of the game draw stream:
        // do not blend widely separated menu, vehicle and race calls into
        // one artificial frame when intermediate native draws are rejected.
        // The original D3D9 Draw always survives these admission failures.
        return submitted < kMaxDraws && ordinal >= slot &&
            ordinal - slot < kMaxDraws;
    }
    // Traverse the complete eligible game Draw population. A legacy fixed
    // 64-draw probe window starved later car-select and race-world draws.
    // Explicit per-frame batch limits remain separate from this CPU cursor.
    static constexpr std::uint32_t next_probe_slot(
        std::uint32_t current, std::uint32_t eligible) noexcept {
        return eligible != 0u && current < eligible - 1u
            ? current + 1u : 0u;
    }
    constexpr bool first_draw() const noexcept { return submitted == 0u; }
    constexpr bool clear_depth() const noexcept { return !depthReady; }
    constexpr bool accepts_depth(bool depth, bool reversed) const noexcept {
        return !depth || depthDirection == 0u ||
               depthDirection == (reversed ? 2u : 1u);
    }
    constexpr void succeeded(bool depth, bool reversed = false) noexcept {
        ++submitted;
        if (depth) {
            depthReady = true;
            depthDirection = reversed ? 2u : 1u;
        }
    }
    constexpr void abort() noexcept { stopped = true; }
    constexpr void reset() noexcept {
        submitted = 0u; stopped = false; depthReady = false;
        depthDirection = 0u;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
