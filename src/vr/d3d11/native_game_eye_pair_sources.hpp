#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace outrun::vr::dx11 {
// Compare canonical IUnknown identities, not interface pointers: two views of
// one eye or an in-flight ring output must never enter CopyResource as a source.
// Reject partially initialized rings rather than trust incomplete provenance.
template <std::size_t N>
[[nodiscard]] constexpr bool native_game_eye_pair_sources_admitted(
    std::uintptr_t left, std::uintptr_t right,
    const std::array<std::uintptr_t, N>& ringOwned) noexcept {
    if (!left || !right || left == right) return false;
    for (const auto identity : ringOwned)
        if (!identity || identity == left || identity == right) return false;
    return true;
}
} // namespace outrun::vr::dx11
