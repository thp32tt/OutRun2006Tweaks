#pragma once
#include <cstdint>
namespace outrun::vr::dx11 {
struct NativeGameOffscreenColorKey {
    std::uintptr_t resource{};
    std::uint32_t arraySlice{}, mipSlice{};
};
// A real GPU copy of a different camera allocation, array eye or mip cannot
// inherit the current eye's offscreen game Draw color provenance.
[[nodiscard]] constexpr bool native_game_offscreen_color_key_matches(
    NativeGameOffscreenColorKey written,
    NativeGameOffscreenColorKey copied) noexcept {
    return written.resource != 0u && copied.resource != 0u &&
        written.resource == copied.resource &&
        written.arraySlice == copied.arraySlice &&
        written.mipSlice == copied.mipSlice;
}
static_assert(native_game_offscreen_color_key_matches(
    {0x1234u, 0u, 0u}, {0x1234u, 0u, 0u}));
static_assert(native_game_offscreen_color_key_matches(
    {0x1234u, 1u, 2u}, {0x1234u, 1u, 2u}));
static_assert(!native_game_offscreen_color_key_matches(
    {0x1234u, 0u, 0u}, {0x5678u, 0u, 0u}));
static_assert(!native_game_offscreen_color_key_matches(
    {0x1234u, 0u, 0u}, {0x1234u, 1u, 0u}));
static_assert(!native_game_offscreen_color_key_matches(
    {0x1234u, 0u, 0u}, {0x1234u, 0u, 1u}));
static_assert(!native_game_offscreen_color_key_matches(
    {}, {0x1234u, 0u, 0u}));
} // namespace outrun::vr::dx11
