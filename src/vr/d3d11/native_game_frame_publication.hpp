#pragma once
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// Full-resolution publication is based on complete real game-source draws,
// same-Present fence provenance and valid output, not an arbitrary pixel
// difference from the old diagnostic inset's constant clear sentinel.
// D3D11 GetData(EVENT) has three materially different outcomes. Only S_OK
// (HRESULT 0) proves that a staging texture is no longer GPU-owned. S_FALSE
// (HRESULT 1) remains in flight; a device error or unexpected status must
// quarantine the resource rather than letting the next game Draw overwrite it.
enum class GameNativeReadbackFence : std::uint8_t { Complete, Pending, Failed };
// A completed GPU EVENT does not imply CPU Map returned usable pixels.
// A failed Map leaves the staging slot quarantined until the owning D3D9
// device Reset; WAS_STILL_DRAWING stays busy but is not an error.
enum class GameNativeReadbackMap : std::uint8_t { Ready, Pending, Failed };
struct GameNativeFramePublication {
    [[nodiscard]] static constexpr GameNativeReadbackFence classify_fence(
        std::int32_t result) noexcept {
        return result == 0 ? GameNativeReadbackFence::Complete :
               result == 1 ? GameNativeReadbackFence::Pending :
                             GameNativeReadbackFence::Failed;
    }
    [[nodiscard]] static constexpr GameNativeReadbackMap classify_map(
        std::int32_t status, std::int32_t stillDrawingStatus,
        bool hasPixels, std::uint32_t width, std::uint32_t rowPitch) noexcept {
        if (status == stillDrawingStatus) return GameNativeReadbackMap::Pending;
        return status == 0 && hasPixels && valid_readback_pitch(width, rowPitch)
            ? GameNativeReadbackMap::Ready : GameNativeReadbackMap::Failed;
    }
    [[nodiscard]] static constexpr bool source_mode_contiguous(
        bool sourceObserved, bool sourceFullMode, bool presentFullMode) noexcept {
        return !sourceObserved || sourceFullMode == presentFullMode;
    }
    [[nodiscard]] static constexpr bool matching_upload_extent(
        std::uint32_t cachedWidth, std::uint32_t cachedHeight,
        std::uint32_t outputWidth, std::uint32_t outputHeight) noexcept {
        return outputWidth != 0u && outputHeight != 0u &&
            cachedWidth == outputWidth && cachedHeight == outputHeight;
    }
    [[nodiscard]] static constexpr bool should_upload(
        bool fullMode, bool complete, bool outputWritable,
        std::uint32_t changedPixels) noexcept {
        return complete && outputWritable && (fullMode || changedPixels != 0u);
    }
    // Real full-size frames may finish out of order in the async staging ring.
    // Select any free staging slot, starting at the next preferred position.
    // An occupied preferred slot must not discard the current menu/race frame
    // when another slot is free; all-busy still preserves original D3D9 input.
    [[nodiscard]] static constexpr std::uint32_t select_available_slot(
        std::uint32_t occupiedMask, std::uint32_t slotCount,
        std::uint32_t preferred) noexcept {
        if (slotCount == 0u || slotCount > 32u || preferred >= slotCount)
            return slotCount;
        for (std::uint32_t offset = 0u; offset < slotCount; ++offset) {
            const std::uint32_t slot = (preferred + offset) % slotCount;
            if ((occupiedMask & (1u << slot)) == 0u) return slot;
        }
        return slotCount;
    }
    // A full-size game image is only useful if its GPU fence completes before
    // this *same* D3D9 Present. Give the already-flushed native submission a
    // bounded opportunity to finish; never wait indefinitely, poll a delayed
    // inset, or substitute an older frame for live game/input.
    static constexpr std::uint32_t kMaxSamePresentExtraPolls = 512u;
    static constexpr std::uint64_t kSamePresentBudgetDivisor = 2000u; // 0.5 ms
    [[nodiscard]] static constexpr bool retry_same_present_fence(
        bool fullMode, bool queuedNow, std::uint32_t extraPolls,
        std::uint64_t elapsedTicks, std::uint64_t frequencyTicks) noexcept {
        return fullMode && queuedNow &&
            extraPolls < kMaxSamePresentExtraPolls &&
            frequencyTicks >= kSamePresentBudgetDivisor &&
            elapsedTicks < frequencyTicks / kSamePresentBudgetDivisor;
    }
    // A completed D3D11 EVENT can briefly precede a nonblocking staging Map.
    // Allow only the just-submitted full-size game frame to reattempt its
    // current-Present Map; older/inset frames never extend their lifetime.
    // A 0.25 ms / 128-attempt ceiling protects the original D3D9 gamepad
    // latency even when the GPU or driver cannot make readback progress.
    static constexpr std::uint32_t kMaxSamePresentMapExtraPolls = 128u;
    static constexpr std::uint64_t kSamePresentMapBudgetDivisor = 4000u;
    [[nodiscard]] static constexpr bool retry_same_present_map(
        bool fullMode, bool queuedNow, bool mapPending,
        std::uint32_t extraPolls, std::uint64_t elapsedTicks,
        std::uint64_t frequencyTicks) noexcept {
        return mapPending && queuedNow && fullMode &&
            extraPolls < kMaxSamePresentMapExtraPolls &&
            frequencyTicks >= kSamePresentMapBudgetDivisor &&
            elapsedTicks < frequencyTicks / kSamePresentMapBudgetDivisor;
    }
    [[nodiscard]] static constexpr bool valid_readback_pitch(
        std::uint32_t width, std::uint32_t rowPitch) noexcept {
        return width != 0u &&
            width <= (std::numeric_limits<std::uint32_t>::max)() / 4u &&
            rowPitch >= width * 4u;
    }
    [[nodiscard]] static constexpr bool valid_upload_pitch(
        std::uint32_t width, std::int32_t rowPitch) noexcept {
        return rowPitch > 0 &&
            valid_readback_pitch(width, static_cast<std::uint32_t>(rowPitch));
    }
};
} // namespace outrun::vr::dx11::live_game_frame
