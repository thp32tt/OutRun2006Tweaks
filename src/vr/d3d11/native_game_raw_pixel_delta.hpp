#pragma once
// RGB changes in an authentic D3D11 pre/post Draw GPU copy pair.
// Do not count a pre-existing clear, stale scene, or alpha-only mutation.
#include <cstdint>
#include <cstddef>
#include <limits>
namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_raw_rgb_changed(
    const std::uint8_t* before, const std::uint8_t* after) noexcept {
    return before[0] != after[0] || before[1] != after[1] ||
           before[2] != after[2];
}
// Query a fence-completed PRE/POST copy before deciding whether to release
// it for another genuine source Draw. Return false on malformed input rather
// than mislabeling invalid mapped memory as a proven RGB-inert capture.
[[nodiscard]] inline bool native_raw_has_rgb_delta(
    const void* before, std::size_t beforePitch,
    const void* after, std::size_t afterPitch,
    std::uint32_t width, std::uint32_t height,
    bool& changed) noexcept {
    changed = false;
    if (!before || !after || !width || !height ||
        width > (std::numeric_limits<std::size_t>::max)() / 4u ||
        beforePitch < std::size_t{width} * 4u ||
        afterPitch < std::size_t{width} * 4u ||
        (height - 1u) > ((std::numeric_limits<std::size_t>::max)() -
            std::size_t{width} * 4u) / beforePitch ||
        (height - 1u) > ((std::numeric_limits<std::size_t>::max)() -
            std::size_t{width} * 4u) / afterPitch) return false;
    const auto* a = static_cast<const std::uint8_t*>(before);
    const auto* b = static_cast<const std::uint8_t*>(after);
    for (std::uint32_t y = 0; y < height; ++y)
        for (std::uint32_t x = 0; x < width; ++x)
            if (native_raw_rgb_changed(
                    a + std::size_t{y} * beforePitch + std::size_t{x} * 4u,
                    b + std::size_t{y} * afterPitch + std::size_t{x} * 4u)) {
                changed = true;
                return true;
            }
    return true;
}
} // namespace outrun::vr::dx11
