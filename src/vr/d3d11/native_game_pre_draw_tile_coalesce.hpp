#pragma once
#include <cstdint>
#include <array>
#include <cstddef>

namespace outrun::vr::dx11::live_game_frame {
// Coalesce ONLY consecutive surviving opaque same-value D3D9 source writes.
// The rectangular union must contain no pixel outside its two operands:
// a bounding-box merge of an L-shape would corrupt a menu/car/race frame.
// Callers compare ARGB/depth values and retire fully superseded writes first.
template<class Tile>
[[nodiscard]] constexpr bool game_native_merge_ordered_overwrite(
    Tile& prior, const Tile& next) noexcept {
    const bool horizontal =
        prior.top == next.top && prior.bottom == next.bottom &&
        prior.left <= next.right && next.left <= prior.right;
    const bool vertical =
        prior.left == next.left && prior.right == next.right &&
        prior.top <= next.bottom && next.top <= prior.bottom;
    if (!horizontal && !vertical) return false;
    if (next.left < prior.left) prior.left = next.left;
    if (next.top < prior.top) prior.top = next.top;
    if (next.right > prior.right) prior.right = next.right;
    if (next.bottom > prior.bottom) prior.bottom = next.bottom;
    return true;
}

// When a later opaque game Clear erases a side of an earlier tile,
// replay only the remaining actual source pixels. A single exact residual
// rectangle is safe without allocating extra GPU tiles. Interior overlap
// or a split into multiple rectangles deliberately keeps the older tile;
// the newer write will overwrite its obsolete pixels in source order.
template<class Tile>
[[nodiscard]] constexpr bool game_native_trim_partially_overwritten(
    Tile& prior, const Tile& next) noexcept {
    const auto l = prior.left > next.left ? prior.left : next.left;
    const auto t = prior.top > next.top ? prior.top : next.top;
    const auto r = prior.right < next.right ? prior.right : next.right;
    const auto b = prior.bottom < next.bottom ? prior.bottom : next.bottom;
    if (l >= r || t >= b) return false;
    if (l <= prior.left && r >= prior.right) {
        if (t <= prior.top && b < prior.bottom) {
            prior.top = b; return true;
        }
        if (b >= prior.bottom && t > prior.top) {
            prior.bottom = t; return true;
        }
    }
    if (t <= prior.top && b >= prior.bottom) {
        if (l <= prior.left && r < prior.right) {
            prior.left = r; return true;
        }
        if (r >= prior.right && l > prior.left) {
            prior.right = l; return true;
        }
    }
    return false;
}
} // namespace outrun::vr::dx11::live_game_frame

/*
 * Authentic source A(row 0), B(row 0), A(row 1), B(row 1)
 * is a two-rectangle RTV/DSV replay, not four. Reordering the older
 * A to the tail is pixel-equivalent ONLY if the exact combined region
 * touches no intervening writer (regardless of that writer's value).
 * This modifies the caller's transaction-local staging buffer only.
 */
template<class Tile, std::size_t Capacity, class SameValue>
[[nodiscard]] constexpr bool game_native_merge_noninterfering_overwrite(
    std::array<Tile, Capacity>& tiles, std::uint32_t count,
    const Tile& next, SameValue&& sameValue) noexcept {
    for (std::uint32_t end = count; end != 0u; --end) {
        const std::uint32_t index = end - 1u;
        if (!sameValue(tiles[index], next)) continue;
        Tile joined = tiles[index];
        if (!game_native_merge_ordered_overwrite(joined, next)) continue;
        bool safe = true;
        for (std::uint32_t between = index + 1u; between < count; ++between) {
            const Tile& intervening = tiles[between];
            const bool intersects =
                joined.left < intervening.right &&
                intervening.left < joined.right &&
                joined.top < intervening.bottom &&
                intervening.top < joined.bottom;
            if (intersects) { safe = false; break; }
        }
        if (!safe) continue;
        // The merged rectangle covers precisely the older + newer pixels,
        // and all displaced game-source writes are nonintersecting.
        for (std::uint32_t i = index + 1u; i < count; ++i)
            tiles[i - 1u] = tiles[i];
        tiles[count - 1u] = joined;
        return true;
    }
    return false;
}
