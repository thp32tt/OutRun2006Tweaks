#pragma once
#include <cstdint>

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
} // namespace outrun::vr::dx11::live_game_frame
