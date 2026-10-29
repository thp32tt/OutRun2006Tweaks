#pragma once
// Pin original D3D9 Draw-surface identity, not the currently bound RT at Present.
namespace outrun::vr::dx11 {
template<typename Surface>
[[nodiscard]] constexpr bool native_raw_source_target_is_presented(
    const Surface* drawTarget, const Surface* presentedBackbuffer) noexcept {
    return drawTarget && drawTarget == presentedBackbuffer;
}
static_assert([]() constexpr {
    int draw = 0, other = 0;
    return native_raw_source_target_is_presented(&draw, &draw) &&
           !native_raw_source_target_is_presented(&draw, &other) &&
           !native_raw_source_target_is_presented(
               static_cast<int*>(nullptr), &draw) &&
           !native_raw_source_target_is_presented(
               &draw, static_cast<int*>(nullptr));
}(), "Source-aligned RAW pixels require exact source Draw backbuffer identity");
} // namespace outrun::vr::dx11
