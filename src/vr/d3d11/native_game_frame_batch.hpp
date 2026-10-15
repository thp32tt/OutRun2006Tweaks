#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Diagnostic compositing only; original D3D9 Draw/Present/input remain intact.
struct GameNativeFrameBatch {
    static constexpr std::uint32_t kMaxDraws = 8u;
    // Complete game-source coverage, independent of the bounded diagnostic inset.
    static constexpr std::uint32_t kMaxFullFrameDraws = 4096u;
    [[nodiscard]] constexpr bool accepts_full(std::uint64_t ordinal) const noexcept {
        // Source ordinals include successful no-op game Draws before the
        // first GPU Draw. They must not suppress the first native RTV clear.
        const std::uint64_t consumed =
            static_cast<std::uint64_t>(submitted) + leadingEmptySourceDraws;
        return !stopped && consumed < kMaxFullFrameDraws &&
            ordinal == consumed &&
            (!hasSourceDraw || lastSourceDraw + 1u == ordinal);
    }
    // A full-resolution image cannot start from a synthetic diagnostic
    // background; require a successful D3D9 full TARGET Clear from the
    // exact source device and render target. Continuing draws keep that seed.
    [[nodiscard]] constexpr bool accepts_full_seeded(
        std::uint64_t ordinal, bool sameSourceFullClear) const noexcept {
        return accepts_full(ordinal) && (submitted != 0u || sameSourceFullClear);
    }
    // A missing/unsupported D3D9 Draw invalidates the full native scene even
    // after the legacy eight-draw inset cap. In diagnostic batch mode, only
    // incomplete inset batches need invalidation; the original D3D9 path
    // remains authoritative regardless of native admission.
    [[nodiscard]] constexpr bool must_abort_unsupported(
        bool fullMode, bool diagnosticBatch) const noexcept {
        return fullMode ||
            (diagnosticBatch && submitted > 0u && submitted < kMaxDraws);
    }
    [[nodiscard]] constexpr bool publishable_full(
        bool pending, std::uint64_t sourceDraws) const noexcept {
        return publishable(pending) && hasSourceDraw &&
            static_cast<std::uint64_t>(submitted) + leadingEmptySourceDraws ==
                sourceDraws &&
            lastSourceDraw + 1u == sourceDraws;
    }
    // Game-created native Draws belong to their source D3D9 device. A
    // foreign Present cannot close the owner's frame or consume its GPU
    // readback. After the owner's Present resets the per-frame draw identity,
    // retain the last valid backbuffer owner for late asynchronous uploads.
    // Without any owner yet, allow probing the first game Present.
    [[nodiscard]] static constexpr bool foreign_present(
        std::uintptr_t sourceDevice, std::uintptr_t lastOutputDevice,
        std::uintptr_t presentingDevice) noexcept {
        return presentingDevice == 0u ||
            (sourceDevice != 0u
                ? sourceDevice != presentingDevice
                : lastOutputDevice != 0u &&
                    lastOutputDevice != presentingDevice);
    }
    // Keep menu/car/race Draw ownership tied to the device which last
    // actually presented a game frame. An auxiliary D3D9 device may draw
    // first after Present, but must not hijack this frame's native batch.
    [[nodiscard]] static constexpr bool admits_game_source(
        std::uintptr_t candidate, std::uintptr_t currentOwner,
        std::uintptr_t lastPresentOwner) noexcept {
        return candidate != 0u &&
            (currentOwner != 0u ? candidate == currentOwner
                               : lastPresentOwner == 0u ||
                                 candidate == lastPresentOwner);
    }
    // At startup no output owner may be known; an auxiliary device can then
    // claim the first source Draw. A VERIFIED successful full-backbuffer Clear
    // on the real game device starts a fresh scene and may recover ownership,
    // but only before any speculative native Draw or pending output.
    [[nodiscard]] static constexpr bool can_reacquire_full_clear(
        std::uintptr_t candidate, std::uintptr_t currentOwner,
        bool fullMode, bool wholeBackbuffer,
        bool nativeSubmitted, bool nativePending) noexcept {
        return fullMode && wholeBackbuffer && candidate != 0u &&
            currentOwner != 0u && candidate != currentOwner &&
            !nativeSubmitted && !nativePending;
    }
    // A menu/auxiliary D3D9 device can Reset while the game's full-size
    // D3D11 Draw and fenced output belong to a different D3D9 device.
    // Never discard the actual game frame, GPU readbacks or input-safe
    // Present continuity in response to that foreign Reset. Before any
    // source/Present owner is known a Reset may still clean startup state.
    [[nodiscard]] static constexpr bool reset_belongs_to_game_source(
        std::uintptr_t resettingDevice, std::uintptr_t sourceOwner,
        std::uintptr_t lastPresentOwner) noexcept {
        return resettingDevice != 0u &&
            (sourceOwner != 0u ? resettingDevice == sourceOwner
                               : lastPresentOwner == 0u ||
                                 resettingDevice == lastPresentOwner);
    }
    std::uint32_t submitted = 0u;
    // Exact successful source ordinals before the first nonempty game Draw.
    // Kept separate because the first real native Draw must still Clear RTV.
    std::uint32_t leadingEmptySourceDraws = 0u;
    bool stopped = false;
    bool depthReady = false;
    // Full game Z-only Clear replaces DSV content without discarding RTV color.
    bool depthClearPending = false;
    float depthClearValue = 1.0f;
    constexpr void note_full_depth_clear(float z) noexcept {
        depthClearPending = true;
        depthClearValue = z;
        depthReady = false;
        depthDirection = 0u;
    }
    [[nodiscard]] constexpr float depth_clear_value(bool reversed) const noexcept {
        return depthClearPending ? depthClearValue : (reversed ? 0.0f : 1.0f);
    }
    constexpr void consume_depth_clear() noexcept { depthClearPending = false; }
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
    // D3D9 may successfully submit a zero-primitive Draw between menu,
    // vehicle and race draws. It writes no pixels, but is still an observed
    // game command: consume its exact source ordinal without dispatching
    // a fabricated D3D11 draw or resetting the native color/depth target.
    // Leading no-op source calls may follow a verified real D3D9 full Clear;
    // preserve their ordinals without claiming a native GPU Draw or frame.
    [[nodiscard]] constexpr bool absorb_empty_source_draw(
        std::uint64_t ordinal, bool sameSourceFullClear = false) noexcept {
        if (!accepts_full(ordinal) ||
            !accepts_source_draw(ordinal, true)) return false;
        if (submitted == 0u) {
            // A successful whole-backbuffer D3D9 Clear is required even for
            // leading empty calls. These consume source order, NOT a GPU
            // submission or the first-draw native Clear/DSV initialization.
            if (!sameSourceFullClear) return false;
            ++leadingEmptySourceDraws;
        } else {
            succeeded(false); // source ordinal only; retain depth direction.
        }
        record_source_draw(ordinal);
        return true;
    }
    // Whole game TARGET then separate whole ZBUFFER Clear can initialize DSV
    // before the first native Draw/DrawIndexed. Never cross an unsupported
    // source Draw or a stopped/partial/foreign game scene.
    [[nodiscard]] constexpr bool can_seed_pre_draw_depth(
        bool sameSourceFullColorClear, bool noSourceDraws) const noexcept {
        // Successful leading no-op game Draws write no depth/color. A separate
        // full Z Clear can still seed the first native race Draw after them.
        const bool onlyLeadingEmpty =
            submitted == 0u && leadingEmptySourceDraws != 0u && hasSourceDraw;
        return sameSourceFullColorClear &&
            (noSourceDraws || onlyLeadingEmpty) && !stopped &&
            submitted == 0u && !depthReady;
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
        depthClearPending = false;
    }
    constexpr void abort() noexcept { stopped = true; depthClearPending = false; }
    constexpr void reset() noexcept {
        submitted = 0u; leadingEmptySourceDraws = 0u;
        stopped = false; depthReady = false;
        depthClearPending = false; depthClearValue = 1.0f;
        depthDirection = 0u;
        lastSourceDraw = 0u; hasSourceDraw = false;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
