#pragma once
#include "native_game_frame_publication.hpp"
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// Map D3D11 BGRA8 output into the independent D3D9 SYSTEMMEM upload.
// Copy only visible bytes, preserving each API's independent row padding.
struct GameNativeFrameUpload {
    // Copy only the source crop that D3D9 Present will reveal. Both GPU and
    // SYSTEMMEM surfaces keep full backbuffer coordinates and independent row
    // strides; outside-crop D3D9 pixels and input remain authoritative.
    [[nodiscard]] static bool copy_rect(
        void* destination, std::int32_t destinationPitch,
        const void* source, std::uint32_t sourcePitch,
        std::uint32_t frameWidth, std::uint32_t frameHeight,
        std::uint32_t left, std::uint32_t top,
        std::uint32_t right, std::uint32_t bottom) noexcept {
        // Validate the complete extent *before* touching upload memory.
        if (!destination || !source || !frameHeight ||
            left >= right || top >= bottom || right > frameWidth || bottom > frameHeight ||
            !GameNativeFramePublication::valid_readback_pitch(frameWidth, sourcePitch) ||
            !GameNativeFramePublication::valid_upload_pitch(frameWidth, destinationPitch))
            return false;
        const std::size_t srcStride = static_cast<std::size_t>(sourcePitch);
        const std::size_t dstStride = static_cast<std::size_t>(destinationPitch);
        const std::size_t rightBytes = static_cast<std::size_t>(right) * 4u;
        const std::size_t leftBytes = static_cast<std::size_t>(left) * 4u;
        const std::size_t copyBytes = rightBytes - leftBytes;
        const std::size_t lastRow = static_cast<std::size_t>(bottom - 1u);
        const std::size_t maxSize = (std::numeric_limits<std::size_t>::max)();
        if (lastRow > (maxSize - rightBytes) / srcStride ||
            lastRow > (maxSize - rightBytes) / dstStride)
            return false;
        auto* dst = static_cast<std::uint8_t*>(destination);
        const auto* src = static_cast<const std::uint8_t*>(source);
        for (std::size_t row = top; row < bottom; ++row)
            std::memcpy(dst + row * dstStride + leftBytes,
                        src + row * srcStride + leftBytes, copyBytes);
        return true;
    }
    [[nodiscard]] static bool copy_rows(
        void* destination, std::int32_t destinationPitch,
        const void* source, std::uint32_t sourcePitch,
        std::uint32_t width, std::uint32_t height) noexcept {
        if (!destination || !source || height == 0u ||
            !GameNativeFramePublication::valid_readback_pitch(width, sourcePitch) ||
            !GameNativeFramePublication::valid_upload_pitch(width, destinationPitch))
            return false;
        const std::size_t rowBytes = static_cast<std::size_t>(width) * 4u;
        const std::size_t dstStride = static_cast<std::size_t>(destinationPitch);
        const std::size_t srcStride = static_cast<std::size_t>(sourcePitch);
        const std::size_t lastRow = static_cast<std::size_t>(height - 1u);
        const std::size_t maxSize = (std::numeric_limits<std::size_t>::max)();
        if (lastRow > (maxSize - rowBytes) / srcStride ||
            lastRow > (maxSize - rowBytes) / dstStride)
            return false;
        auto* dst = static_cast<std::uint8_t*>(destination);
        const auto* src = static_cast<const std::uint8_t*>(source);
        for (std::size_t row = 0; row < height; ++row)
            std::memcpy(dst + row * dstStride, src + row * srcStride, rowBytes);
        return true;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
