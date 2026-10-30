#pragma once
// Pick the highest-evidence subset of a REAL paired D3D11 Draw snapshot.
// No invented/repeated pixels, scene coverage, stereo or full-frame claims.
// This runs only in the user's explicit RAW visual diagnostic mode.
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
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

    // Count only RGB pixels produced by the captured native GPU Draw in
    // this exact, unscaled source subrectangle (not its bounding box).
    [[nodiscard]] std::uint32_t changed_pixels(
        const NativeRawPresentTile& tile) const noexcept {
        if (!windowWidth_ || !windowHeight_ ||
            !tile.copyWidth || !tile.copyHeight ||
            tile.copyWidth > windowWidth_ || tile.copyHeight > windowHeight_ ||
            tile.sourceX > windowWidth_ - tile.copyWidth ||
            tile.sourceY > windowHeight_ - tile.copyHeight)
            return 0u;
        return count(tile.sourceX, tile.sourceY,
                     tile.copyWidth, tile.copyHeight);
    }

    // Retain only GPU-changed RGB on an authenticated original-screen tile.
    // Reserving a huge source box for one changed pixel can hide the next
    // overlapping native Draw even when that Draw changes a different pixel.
    [[nodiscard]] bool tighten_to_rgb_bounds(
        const NativeRawPresentTile& tile, NativeRawPresentTile& tight,
        std::uint32_t& rgb) const noexcept {
        tight = {};
        rgb = changed_pixels(tile);
        if (!rgb || tile.destinationX < 0 || tile.destinationY < 0)
            return false;
        std::uint32_t left = 0u, top = 0u;
        std::uint32_t right = tile.copyWidth - 1u;
        std::uint32_t bottom = tile.copyHeight - 1u;
        while (left < right && !count(tile.sourceX + left,
                                      tile.sourceY, 1u, tile.copyHeight)) ++left;
        while (right > left && !count(tile.sourceX + right,
                                      tile.sourceY, 1u, tile.copyHeight)) --right;
        const auto keptWidth = right - left + 1u;
        while (top < bottom && !count(tile.sourceX + left,
                                      tile.sourceY + top, keptWidth, 1u)) ++top;
        while (bottom > top && !count(tile.sourceX + left,
                                      tile.sourceY + bottom, keptWidth, 1u)) --bottom;
        if (tile.destinationX > (std::numeric_limits<std::int64_t>::max)() - left ||
            tile.destinationY > (std::numeric_limits<std::int64_t>::max)() - top)
            return false;
        tight = tile;
        tight.sourceX += left;
        tight.sourceY += top;
        tight.destinationX += static_cast<std::int64_t>(left);
        tight.destinationY += static_cast<std::int64_t>(top);
        tight.copyWidth = keptWidth;
        tight.copyHeight = bottom - top + 1u;
        return changed_pixels(tight) == rgb;
    }

    // Find the largest fully native-RGB rectangle in the same original
    // game source coordinates. A wide top row above several narrower rows
    // defeats a horizontal-run-only search: it misses the taller rectangle
    // beginning *inside* the wider row and consumes extra Present slots.
    // A bounded monotonic histogram scans each authentic GPU delta pixel
    // once per row, O(width * height), without heap or invented pixels.
    [[nodiscard]] bool select_solid_rgb_tile(
        const NativeRawPresentTile& tile, NativeRawPresentTile& solid,
        std::uint32_t& rgb) const noexcept {
        solid = {};
        rgb = 0u;
        const auto total = changed_pixels(tile);
        if (!total || tile.destinationX < 0 || tile.destinationY < 0)
            return false;
        const std::uint64_t area =
            std::uint64_t{tile.copyWidth} * tile.copyHeight;
        if (total == area) {
            solid = tile;
            rgb = total;
            return true;
        }
        // changed_pixels proved the bounded source footprint (<=256x144).
        std::array<std::uint32_t, kWidth> heights{};
        std::array<std::uint32_t, kWidth> stack{};
        constexpr auto max = (std::numeric_limits<std::int64_t>::max)();
        for (std::uint32_t y = 0u; y < tile.copyHeight; ++y) {
            for (std::uint32_t x = 0u; x < tile.copyWidth; ++x)
                heights[x] = count(tile.sourceX + x, tile.sourceY + y,
                                   1u, 1u) ? heights[x] + 1u : 0u;
            std::uint32_t depth = 0u;
            // The sentinel flushes the final rising histogram. Equal-size
            // candidates keep the first deterministic source position.
            for (std::uint32_t x = 0u; x <= tile.copyWidth; ++x) {
                const auto nextHeight = x < tile.copyWidth ? heights[x] : 0u;
                while (depth && heights[stack[depth - 1u]] > nextHeight) {
                    const auto h = heights[stack[--depth]];
                    const auto left = depth ? stack[depth - 1u] + 1u : 0u;
                    const auto w = x - left;
                    const auto pixels = w * h;
                    if (pixels <= rgb) continue;
                    const auto top = y + 1u - h;
                    if (tile.destinationX > max - left ||
                        tile.destinationY > max - top) continue;
                    NativeRawPresentTile candidate = tile;
                    candidate.sourceX += left;
                    candidate.sourceY += top;
                    candidate.destinationX += static_cast<std::int64_t>(left);
                    candidate.destinationY += static_cast<std::int64_t>(top);
                    candidate.copyWidth = w;
                    candidate.copyHeight = h;
                    solid = candidate;
                    rgb = pixels;
                }
                if (x < tile.copyWidth) stack[depth++] = x;
            }
        }
        // No density guess: authenticate every pixel in the selected GPU
        // rectangle before D3D9 original-screen UpdateSurface can use it.
        return rgb != 0u && changed_pixels(solid) == rgb &&
            std::uint64_t{solid.copyWidth} * solid.copyHeight == rgb;
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
