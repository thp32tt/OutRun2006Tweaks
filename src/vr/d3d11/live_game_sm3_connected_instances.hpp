#pragma once
// Convert D3D9 instanced line strips, triangle strips and triangle fans to
// independent indexed lists for a single native D3D11 DrawIndexed.
// Never connect neighboring source-instance primitive boundaries.
// Also handles a single trailing instance in the final segmented GPU upload.
#include <cstdint>
#include <limits>
#include <vector>
namespace outrun::vr::dx11::live_game_frame {
[[nodiscard]] inline bool game_sm3_expand_connected_instance_indices(
    std::uint32_t primitiveType, const std::uint32_t* sourceIndices,
    std::uint32_t sourceCount, std::uint32_t verticesPerInstance,
    std::uint32_t instanceCount, std::uint32_t maxIndices,
    std::vector<std::uint32_t>& destination) noexcept {
    const bool lineStrip = primitiveType == 3u;
    const bool triangleStrip = primitiveType == 5u;
    const bool triangleFan = primitiveType == 6u;
    if ((!lineStrip && !triangleStrip && !triangleFan) ||
        sourceCount < (lineStrip ? 2u : 3u) ||
        !verticesPerInstance || !instanceCount || !maxIndices)
        return false;
    const std::uint64_t vertices =
        std::uint64_t(verticesPerInstance) * instanceCount;
    const std::uint64_t primitives =
        std::uint64_t(sourceCount) - (lineStrip ? 1u : 2u);
    const std::uint64_t perInstanceIndices = primitives * (lineStrip ? 2u : 3u);
    const std::uint64_t totalIndices = perInstanceIndices * instanceCount;
    if (vertices > (std::numeric_limits<std::int32_t>::max)() ||
        totalIndices > maxIndices || totalIndices > (1ull << 25u) / sizeof(std::uint32_t))
        return false;
    for (std::uint32_t i = 0u; i < sourceCount; ++i)
        if ((sourceIndices ? sourceIndices[i] : i) >= verticesPerInstance)
            return false;
    try {
        std::vector<std::uint32_t> fresh(static_cast<std::size_t>(totalIndices));
        for (std::uint32_t instance = 0u; instance < instanceCount; ++instance) {
            const std::uint32_t base = instance * verticesPerInstance;
            const std::size_t first =
                static_cast<std::size_t>(instance) * static_cast<std::size_t>(perInstanceIndices);
            for (std::uint32_t primitive = 0u; primitive < primitives; ++primitive) {
                const auto at = [&](std::uint32_t i) noexcept -> std::uint32_t {
                    return base + (sourceIndices ? sourceIndices[i] : i);
                };
                const std::size_t pos = first +
                    static_cast<std::size_t>(primitive) * (lineStrip ? 2u : 3u);
                if (lineStrip) {
                    fresh[pos] = at(primitive);
                    fresh[pos + 1u] = at(primitive + 1u);
                } else if (triangleFan) {
                    fresh[pos] = at(0u);
                    fresh[pos + 1u] = at(primitive + 1u);
                    fresh[pos + 2u] = at(primitive + 2u);
                } else {
                    // Preserve the original D3D9 strip's alternating winding
                    // (and hence the actual CW/CCW cull result).
                    fresh[pos] = at(primitive + (primitive & 1u));
                    fresh[pos + 1u] = at(primitive + 1u - (primitive & 1u));
                    fresh[pos + 2u] = at(primitive + 2u);
                }
            }
        }
        destination.swap(fresh);
        return true;
    } catch (...) { return false; }
}
} // namespace outrun::vr::dx11::live_game_frame
