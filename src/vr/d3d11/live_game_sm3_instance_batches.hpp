#pragma once
// Portable source-authored D3D9 instance-list IB -> native DrawIndexed buffer.
#include <cstdint>
#include <limits>
#include <vector>
namespace outrun::vr::dx11::live_game_frame {
[[nodiscard]] constexpr bool game_sm3_independent_list(std::uint32_t t) noexcept {
    // D3DPT_POINTLIST, D3DPT_LINELIST, D3DPT_TRIANGLELIST.
    return t == 1u || t == 2u || t == 4u;
}
[[nodiscard]] inline bool game_sm3_expand_list_instance_indices(
    const std::uint32_t* indices, std::uint32_t indexCount,
    std::uint32_t verticesPerInstance, std::uint32_t instances,
    std::vector<std::uint32_t>& destination) noexcept {
    if (!indices || !indexCount || !verticesPerInstance || instances < 2u)
        return false;
    const auto vCount = std::uint64_t(verticesPerInstance) * instances;
    const auto iCount = std::uint64_t(indexCount) * instances;
    if (vCount > (std::numeric_limits<std::int32_t>::max)() ||
        iCount > (1ull << 25u) / sizeof(std::uint32_t)) return false;
    for (std::uint32_t i = 0u; i < indexCount; ++i)
        if (indices[i] >= verticesPerInstance) return false;
    try {
        std::vector<std::uint32_t> fresh(static_cast<std::size_t>(iCount));
        for (std::uint32_t n = 0u; n < instances; ++n) {
            const auto offset = n * verticesPerInstance;
            const auto out = std::size_t(n) * indexCount;
            for (std::uint32_t i = 0u; i < indexCount; ++i)
                fresh[out + i] = offset + indices[i];
        }
        destination.swap(fresh); // unsuccessful plans cannot corrupt a prior draw
        return true;
    } catch (...) { return false; }
}
} // namespace outrun::vr::dx11::live_game_frame
