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
} // namespace outrun::vr::dx11::live_game_stereo
