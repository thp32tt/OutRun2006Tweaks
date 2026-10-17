#pragma once
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_stereo {
// Hardware instancing is a single source-authored command/clear ordinal.
// A zero-instance call writes no pixels and cannot establish an XR eye.
[[nodiscard]] constexpr bool may_issue_instanced(
    std::uint32_t elementsPerInstance, std::uint32_t instanceCount,
    std::uint64_t issuedCommands) noexcept {
    return elementsPerInstance != 0u && instanceCount != 0u &&
        issuedCommands != (std::numeric_limits<std::uint64_t>::max)();
}
// D3D11 occlusion predicates can suppress a submitted GPU Draw without
// an API failure. Never claim that draw as color evidence for native stereo.
[[nodiscard]] constexpr bool color_certifiable(
    bool colorWritable, bool noActivePredicate) noexcept {
    return colorWritable && noActivePredicate;
}
// A completed game-authored Copy/Stretch can be the final visible color
// source for a depth-only on-eye Draw (offscreen menu/car/race composition).
// Still require at least one real geometry Draw and the existing independently
// validated view/pose evidence; postpasses do NOT fabricate Draw ordinals.
[[nodiscard]] constexpr bool authored_color_output_ready(
    std::uint64_t geometryDraws, std::uint64_t directColorDraws,
    std::uint32_t authoredColorPostpasses) noexcept {
    return geometryDraws != 0u &&
           (directColorDraws != 0u || authoredColorPostpasses != 0u);
}
static_assert(authored_color_output_ready(2u, 0u, 1u));
static_assert(authored_color_output_ready(1u, 1u, 0u));
static_assert(!authored_color_output_ready(0u, 0u, 1u));
static_assert(!authored_color_output_ready(4u, 0u, 0u));
} // namespace outrun::vr::dx11::live_game_stereo
