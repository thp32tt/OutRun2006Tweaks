#pragma once
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// Full-resolution publication is based on complete real game-source draws,
// same-Present fence provenance and valid output, not an arbitrary pixel
// difference from the old diagnostic inset's constant clear sentinel.
struct GameNativeFramePublication {
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
