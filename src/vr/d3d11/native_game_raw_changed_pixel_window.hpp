#pragma once
// Pick the highest-evidence subset of a REAL paired D3D11 Draw snapshot.
// No invented/repeated pixels, scene coverage, stereo or full-frame claims.
// This runs only in the user's explicit RAW visual diagnostic mode.
#include <array>
#include <cstddef>
#include <cstdint>
#include "native_game_raw_partial_present_tile.hpp"
#include "native_game_raw_pixel_delta.hpp"

namespace outrun::vr::dx11 {
class NativeRawChangedPixelWindow final {
public:
    static constexpr std::uint32_t kWidth = 256u;
    static constexpr std::uint32_t kHeight = 144u;
    static constexpr std::size_t kStride = kWidth + 1u;

    // Caller owns the mapped, format-validated before/after staging images.
    // RGB delta deliberately ignores source alpha, matching visible evidence.
    void capture(const void* before, std::size_t beforePitch,
                 const void* after, std::size_t afterPitch,
                 std::uint32_t captureWidth = kWidth,
                 std::uint32_t captureHeight = kHeight) noexcept {
        prefix_.fill(0u);
        // A game-created menu/vehicle surface can be smaller than the
        // 256x144 diagnostic maximum. Keep the same fixed-size scratch
        // buffer but admit only bytes copied from that authentic target.
        windowWidth_ = captureWidth <= kWidth ? captureWidth : 0u;
        windowHeight_ = captureHeight <= kHeight ? captureHeight : 0u;
        if (!windowWidth_ || !windowHeight_ || !before || !after ||
            beforePitch < std::size_t{windowWidth_} * 4u ||
            afterPitch < std::size_t{windowWidth_} * 4u) {
            windowWidth_ = windowHeight_ = 0u;
            return;
        }
        const auto* beforeBytes = static_cast<const std::uint8_t*>(before);
        const auto* afterBytes = static_cast<const std::uint8_t*>(after);
        for (std::uint32_t y = 0; y < windowHeight_; ++y) {
            std::uint32_t rowDelta = 0u;
            for (std::uint32_t x = 0; x < windowWidth_; ++x) {
                const auto offset = std::size_t{x} * 4u;
                rowDelta += native_raw_rgb_changed(
                    beforeBytes + std::size_t{y} * beforePitch + offset,
                    afterBytes + std::size_t{y} * afterPitch + offset) ? 1u : 0u;
                prefix_[std::size_t{y + 1u} * kStride + x + 1u] =
                    prefix_[std::size_t{y} * kStride + x + 1u] + rowDelta;
            }
        }
    }

    // D3D9 source crop and destination remain unchanged. Scan all legal
    // unscaled GPU source windows; select the one with MOST actual changed RGB.
    // On equal evidence retain the previously centered tile (no jitter).
    [[nodiscard]] bool select(const NativeRawPresentTile& original,
                              NativeRawPresentTile& selected,
                              std::uint32_t& visibleChangedPixels) const noexcept {
        selected = {};
        visibleChangedPixels = 0u;
        if (!windowWidth_ || !windowHeight_ ||
            !original.copyWidth || !original.copyHeight ||
            original.copyWidth > windowWidth_ ||
            original.copyHeight > windowHeight_ ||
            original.sourceX > windowWidth_ - original.copyWidth ||
            original.sourceY > windowHeight_ - original.copyHeight)
            return false;
        selected = original;
        visibleChangedPixels = count(original.sourceX, original.sourceY,
                                     original.copyWidth, original.copyHeight);
        if (visibleChangedPixels == original.copyWidth * original.copyHeight)
            return true; // An already-perfect authentic crop cannot improve.
        const auto rightmost = windowWidth_ - original.copyWidth;
        const auto bottommost = windowHeight_ - original.copyHeight;
        for (std::uint32_t y = 0; y <= bottommost; ++y) {
            for (std::uint32_t x = 0; x <= rightmost; ++x) {
                const auto changed = count(x, y, original.copyWidth,
                                           original.copyHeight);
                if (changed > visibleChangedPixels) {
                    visibleChangedPixels = changed;
                    selected.sourceX = x;
                    selected.sourceY = y;
                }
            }
        }
        return true;
    }

private:
    [[nodiscard]] std::uint32_t count(std::uint32_t x, std::uint32_t y,
                                      std::uint32_t w, std::uint32_t h) const noexcept {
        const auto tl = std::size_t{y} * kStride + x;
        const auto tr = tl + w;
        const auto bl = std::size_t{y + h} * kStride + x;
        const auto br = bl + w;
        return prefix_[br] - prefix_[tr] - prefix_[bl] + prefix_[tl];
    }
    // Inclusive prefix of genuine GPU RGB deltas; max sum is 256*144.
    // Keep scratch storage on the preview owner, not a large hook-call stack.
    std::array<std::uint32_t, (kWidth + 1u) * (kHeight + 1u)> prefix_{};
    std::uint32_t windowWidth_ = 0u, windowHeight_ = 0u;
};
} // namespace outrun::vr::dx11
