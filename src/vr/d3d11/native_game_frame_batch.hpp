#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Diagnostic compositing only; original D3D9 Draw/Present/input remain intact.
struct GameNativeFrameBatch {
    static constexpr std::uint32_t kMaxDraws = 8u;
    std::uint32_t submitted = 0u;
    bool stopped = false;
    bool depthReady = false;
    // Raw observed game call indices, NOT only the admitted FVF candidates.
    // Unsupported/interleaved D3D9 draws cannot be spliced into a native scene.
    std::uint64_t lastSourceDraw = 0u;
    bool hasSourceDraw = false;
    // Inset Z accumulation cannot mix forward and reverse D3D9 comparisons.
    std::uint32_t depthDirection = 0u;
    constexpr bool accepts(std::uint32_t ordinal, std::uint32_t slot,
                           bool multi) const noexcept {
        if (stopped) return false;
        if (!multi) return submitted == 0u && ordinal == slot;
        // A batch represents one contiguous slice of the game draw stream:
        // do not blend skipped, reordered, or widely separated game calls into
        // one artificial frame when intermediate native draws are rejected.
        // The original D3D9 Draw always survives these admission failures.
        return submitted < kMaxDraws && ordinal >= slot &&
            ordinal - slot == submitted && ordinal - slot < kMaxDraws;
    }
    constexpr bool accepts_source_draw(std::uint64_t ordinal, bool multi) const noexcept {
        return !stopped && (!multi || submitted == 0u ||
               (hasSourceDraw && ordinal > lastSourceDraw &&
                ordinal - lastSourceDraw == 1u));
    }
    constexpr void record_source_draw(std::uint64_t ordinal) noexcept {
        lastSourceDraw = ordinal;
        hasSourceDraw = true;
    }
    // An aborted batch must never reach the GPU readback/inset presenter,
    // even if one or more of its D3D11 Draw calls already ran.
    constexpr bool publishable(bool pending) const noexcept {
        return pending && submitted != 0u && !stopped;
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
    // A real game color/depth Clear or main render-target switch divides the
    // Draw stream into different scenes. Even a completed eight-draw batch is
    // invalid if its pixels were subsequently cleared before Present.
    constexpr void scene_boundary() noexcept {
        if (submitted != 0u) stopped = true;
    }
    constexpr void abort() noexcept { stopped = true; }
    constexpr void reset() noexcept {
        submitted = 0u; stopped = false; depthReady = false;
        depthDirection = 0u;
        lastSourceDraw = 0u; hasSourceDraw = false;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
