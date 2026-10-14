#pragma once
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// Full-resolution publication is based on complete real game-source draws,
// same-Present fence provenance and valid output, not an arbitrary pixel
// difference from the old diagnostic inset's constant clear sentinel.
struct GameNativeFramePublication {
    [[nodiscard]] static constexpr bool should_upload(
        bool fullMode, bool complete, bool outputWritable,
        std::uint32_t changedPixels) noexcept {
        return complete && outputWritable && (fullMode || changedPixels != 0u);
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
