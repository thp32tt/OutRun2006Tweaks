#pragma once
// Portable admission contract for live game-authored D3D9 MIN/MAX blend.
// D3D9 enum values: ONE=2, SRCALPHA=5, INVSRCALPHA=6; MIN=4, MAX=5.
// These operations ignore both blending factors in D3D9 and D3D11.
// Keep the native diagnostic restricted to already known RGB factor pairs
// and no independent alpha equation; original D3D9 Draw/input is untouched.
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
constexpr bool game_native_extremum_admission(
    std::uint32_t operation, std::uint32_t source, std::uint32_t destination,
    bool separateAlpha, std::uint32_t writeMask) noexcept {
    const bool knownPair = (source == 5u && destination == 6u) ||
                           (source == 2u && destination == 2u) ||
                           (source == 5u && destination == 2u) ||
                           (source == 2u && destination == 6u);
    return (operation == 4u || operation == 5u) && knownPair &&
           !separateAlpha && (writeMask & ~15u) == 0u &&
           (writeMask & 7u) != 0u;
}
constexpr std::uint32_t game_native_extremum_slot(
    bool maximum, std::uint32_t pairVariant,
    std::uint32_t writeMask) noexcept {
    return ((maximum ? 1u : 0u) * 4u + pairVariant) * 16u + writeMask;
}
static_assert(game_native_extremum_admission(4,5,6,false,15));
static_assert(game_native_extremum_admission(5,2,2,false,7));
static_assert(game_native_extremum_slot(false,0,15) !=
              game_native_extremum_slot(true,0,15));
static_assert(game_native_extremum_slot(true,3,15) == 127u);
static_assert(!game_native_extremum_admission(3,5,6,false,15));
static_assert(!game_native_extremum_admission(4,2,1,false,15));
static_assert(!game_native_extremum_admission(5,5,6,true,15));
static_assert(!game_native_extremum_admission(4,5,6,false,8));
} // namespace outrun::vr::dx11::live_game_frame
