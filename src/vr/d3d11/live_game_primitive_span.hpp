#pragma once

#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// Common bound for actual D3D9 VB/IB/UP snapshots and D3D11 Draw/DrawIndexed.
// A strip has P+2 source elements; a list has P*3. Never infer either from
// the other: overreading a live game pointer could break the original draw.
constexpr bool game_primitive_element_count(bool triangleStrip,
                                             std::uint32_t primitiveCount,
                                             std::uint32_t& elements) noexcept {
    if (primitiveCount == 0u || primitiveCount > 512u) return false;
    const std::uint64_t required = triangleStrip
        ? static_cast<std::uint64_t>(primitiveCount) + 2u
        : static_cast<std::uint64_t>(primitiveCount) * 3u;
    if (required > 1536u) return false;
    elements = static_cast<std::uint32_t>(required);
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
