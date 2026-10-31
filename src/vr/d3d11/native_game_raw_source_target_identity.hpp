#pragma once
// Pin original D3D9 Draw-surface identity, not the currently bound RT at Present.
namespace outrun::vr::dx11 {
template<typename Surface>
[[nodiscard]] constexpr bool native_raw_source_target_is_presented(
    const Surface* drawTarget, const Surface* presentedBackbuffer) noexcept {
    return drawTarget && drawTarget == presentedBackbuffer;
}
// Comparing an interface pointer is insufficient for a COM object: two
// interface pointers can represent the SAME underlying game backbuffer.
// Only the canonical IID_IUnknown identity may authorize source-coincident
// native GPU RGB. Both original surface handles must remain live.
template <typename DrawSurface, typename PresentSurface, typename Identity>
[[nodiscard]] constexpr bool native_raw_canonical_source_target_is_presented(
    const DrawSurface* drawTarget, const PresentSurface* presentedBackbuffer,
    const Identity* drawUnknown, const Identity* presentedUnknown) noexcept {
    return drawTarget && presentedBackbuffer &&
        native_raw_source_target_is_presented(drawUnknown, presentedUnknown);
}
static_assert([]() constexpr {
    int draw = 0, other = 0;
    return native_raw_source_target_is_presented(&draw, &draw) &&
           native_raw_canonical_source_target_is_presented(
               &draw, &other, &draw, &draw) &&
           !native_raw_canonical_source_target_is_presented(
               &draw, &other, &draw, &other) &&
           !native_raw_canonical_source_target_is_presented(
               static_cast<int*>(nullptr), &other, &draw, &draw) &&
           !native_raw_canonical_source_target_is_presented(
               &draw, &other, static_cast<int*>(nullptr), &draw) &&
           !native_raw_source_target_is_presented(&draw, &other) &&
           !native_raw_source_target_is_presented(
               static_cast<int*>(nullptr), &draw) &&
           !native_raw_source_target_is_presented(
               &draw, static_cast<int*>(nullptr));
}(), "Source-aligned RAW pixels require exact source Draw backbuffer identity");
} // namespace outrun::vr::dx11
