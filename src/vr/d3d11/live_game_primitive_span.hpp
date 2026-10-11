#pragma once

#include <cstdint>
#include <vector>

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
 
// D3D9 fan (P+2 source elements) becomes P*3 indexed D3D11 triangles.
// Bounds and winding are preserved. On a bad source, output stays unchanged.
inline bool game_fan_to_triangle_list(std::uint32_t primitiveCount,
                                     const std::uint32_t* sourceIndices,
                                     std::uint32_t sourceIndexCount,
                                     std::uint32_t vertexCount,
                                     std::vector<std::uint32_t>& triangles) {
    std::uint32_t required = 0;
    if (!game_primitive_element_count(true, primitiveCount, required) ||
        vertexCount == 0u || vertexCount > 1536u) return false;
    if (sourceIndices) {
        if (sourceIndexCount != required) return false;
    } else if (sourceIndexCount != 0u || vertexCount != required) return false;
    std::vector<std::uint32_t> result;
    result.reserve(static_cast<std::size_t>(primitiveCount) * 3u);
    const std::uint32_t center = sourceIndices ? sourceIndices[0] : 0u;
    if (center >= vertexCount) return false;
    for (std::uint32_t i = 0; i < primitiveCount; ++i) {
        const std::uint32_t b = sourceIndices ? sourceIndices[i + 1u] : i + 1u;
        const std::uint32_t c = sourceIndices ? sourceIndices[i + 2u] : i + 2u;
        if (b >= vertexCount || c >= vertexCount) return false;
        result.push_back(center);
        result.push_back(b);
        result.push_back(c);
    }
    triangles.swap(result);
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
