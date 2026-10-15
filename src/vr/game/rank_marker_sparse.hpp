#pragma once
// R84 exact rank/rival sprite batch: bound CPU work to GPU-referenced vertices.
// Never interpret untrusted/mixed sprite batches as one projected vehicle.
// Non-indexed, missing or inconsistent hints retain the original dense path.
#include <cstddef>
#include <cstdint>
#include <vector>

namespace OutRunVR::RankMarker
{
    struct SparseRankPlan
    {
        bool enabled = false;
        std::size_t referenced = 0;
    };

    inline SparseRankPlan PlanSparseRankVertices(
        std::size_t vertexCount, const std::vector<std::uint8_t>* usedMask,
        const std::vector<std::uint32_t>* touched,
        std::size_t knownUsedCount) noexcept
    {
        if (!usedMask || !touched || vertexCount < 64u ||
            knownUsedCount == 0u || knownUsedCount != touched->size() ||
            knownUsedCount > vertexCount / 4u ||
            usedMask->size() < vertexCount)
            return {};
        // Touched lists are built from the leased, unique index decoder.
        // Corrupt/out-of-range memberships never enter a partial copy.
        for (const auto index : *touched)
            if (index >= vertexCount || !(*usedMask)[index])
                return {};
        return {true, knownUsedCount};
    }
}
