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
// Source-authored independent D3D9 POINT/LINE/TRIANGLE lists may reuse
// their same source IB across many instances. If duplicating the entire IB
// would exceed the bounded native upload, submit independent native indexed
// draws using each instance's materialized vertex base instead of rejecting
// valid game geometry. Non-indexed lists can still use one contiguous Draw.
enum class GameSm3ListSubmissionMode : std::uint8_t {
    invalid, compact_indexed, compact_linear, per_instance
};
struct GameSm3ListSubmissionPlan {
    GameSm3ListSubmissionMode mode = GameSm3ListSubmissionMode::invalid;
    std::uint32_t drawCount = 0u;
};
[[nodiscard]] constexpr GameSm3ListSubmissionPlan
game_sm3_list_submission_plan(std::uint32_t primitiveType, bool indexed,
    std::uint32_t sourceCount, std::uint32_t verticesPerInstance,
    std::uint32_t instanceCount, std::uint32_t maxExpandedIndices) noexcept {
    const bool list = game_sm3_independent_list(primitiveType);
    const std::uint32_t group = primitiveType == 2u ? 2u :
                                primitiveType == 4u ? 3u : 1u;
    if (!list || !sourceCount || sourceCount % group != 0u ||
        !verticesPerInstance || instanceCount < 2u || !maxExpandedIndices ||
        (indexed && sourceCount > maxExpandedIndices))
        return {};
    const auto expandedVertices =
        std::uint64_t(verticesPerInstance) * instanceCount;
    if (expandedVertices > (std::numeric_limits<std::int32_t>::max)())
        return {};  // a D3D11 BaseVertexLocation cannot represent it
    if (!indexed)
        return {GameSm3ListSubmissionMode::compact_linear, 1u};
    constexpr std::uint64_t maxTemporaryIndices =
        (1ull << 25u) / sizeof(std::uint32_t);
    const std::uint64_t allowed =
        maxExpandedIndices < maxTemporaryIndices ?
        maxExpandedIndices : maxTemporaryIndices;
    if (std::uint64_t(sourceCount) <= allowed / instanceCount)
        return {GameSm3ListSubmissionMode::compact_indexed, 1u};
    return {GameSm3ListSubmissionMode::per_instance, instanceCount};
}
// The game's genuine INDEXEDDATA/INSTANCEDATA mesh has already been packed
// into consecutive FLOAT4 D3D11 vertices. Independent D3D9 point, line and
// triangle *lists* may be submitted once per bounded GPU upload rather than
// issuing a Draw for every source instance. Connected strips/fans and point
// fill are not lists: they retain separate source primitive boundaries.
// If an expanded indexed list cannot fit the original transient index budget,
// fall back to one indexed Draw per source instance without enlarging buffers.
struct GameSm3SegmentedListSubmission {
    bool grouped = false;
    std::uint32_t batches = 0u;
};
[[nodiscard]] constexpr GameSm3SegmentedListSubmission
game_sm3_segmented_list_submission_plan(
    std::uint32_t primitiveType, bool indexed, bool pointFill,
    std::uint32_t instanceCount, std::uint32_t instancesPerUpload,
    std::uint32_t sourceIndexCount, std::uint32_t maxExpandedIndices) noexcept {
    if (!game_sm3_independent_list(primitiveType) || pointFill ||
        !instanceCount || instancesPerUpload < 2u ||
        instanceCount <= instancesPerUpload)
        return {};
    if (indexed && (!sourceIndexCount || !maxExpandedIndices ||
                    std::uint64_t(sourceIndexCount) * instancesPerUpload >
                        maxExpandedIndices ||
                    std::uint64_t(sourceIndexCount) * instancesPerUpload >
                        (1ull << 25u) / sizeof(std::uint32_t)))
        return {};
    return {true, static_cast<std::uint32_t>(
        (std::uint64_t(instanceCount) + instancesPerUpload - 1u) /
        instancesPerUpload)};
}

} // namespace outrun::vr::dx11::live_game_frame
