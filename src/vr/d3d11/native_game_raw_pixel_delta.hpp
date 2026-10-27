#pragma once
// RGB changes in an authentic D3D11 pre/post Draw GPU copy pair.
// Do not count a pre-existing clear, stale scene, or alpha-only mutation.
#include <cstdint>
namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_raw_rgb_changed(
    const std::uint8_t* before, const std::uint8_t* after) noexcept {
    return before[0] != after[0] || before[1] != after[1] ||
           before[2] != after[2];
}
} // namespace outrun::vr::dx11
