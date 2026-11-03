#pragma once
// Preserve a source-authored D3D9 instanced connected primitive when expanding
// every instance to one DrawIndexed would exceed the transient index budget.
// Small batches retain the efficient one-Draw expansion. Large, valid batches
// use per-instance native Draw/DrawIndexed with independent strip/fan edges.
#include <algorithm>
#include <cstdint>
#include <limits>
namespace outrun::vr::dx11::live_game_frame {
enum class GameSm3ConnectedSubmissionMode : std::uint8_t {
    invalid, compact_indexed, per_instance
};
struct GameSm3ConnectedSubmissionPlan {
    GameSm3ConnectedSubmissionMode mode = GameSm3ConnectedSubmissionMode::invalid;
    std::uint32_t drawCount = 0u;
};
[[nodiscard]] constexpr GameSm3ConnectedSubmissionPlan
game_sm3_connected_submission_plan(std::uint32_t primitiveType,
    std::uint32_t sourceCount, std::uint32_t verticesPerInstance,
    std::uint32_t instanceCount, std::uint32_t maxExpandedIndices) noexcept {
    const bool lineStrip = primitiveType == 3u;
    if ((!lineStrip && primitiveType != 5u && primitiveType != 6u) ||
        sourceCount < (lineStrip ? 2u : 3u) || !verticesPerInstance ||
        instanceCount < 2u || !maxExpandedIndices)
        return {};
    const auto countPerInstance =
        (std::uint64_t(sourceCount) - (lineStrip ? 1u : 2u)) *
        (lineStrip ? 2u : 3u);
    // Integer division avoids overflow when the live game specifies large
    // instance counts. Segmentation never allocates an expanded index list.
    constexpr std::uint64_t maxTemporaryIndices = (1ull << 25u) / 4u;
    const auto allowed = (std::min)(
        std::uint64_t(maxExpandedIndices), maxTemporaryIndices);
    const bool compact = countPerInstance <= allowed / instanceCount &&
        std::uint64_t(verticesPerInstance) * instanceCount <=
            std::uint64_t((std::numeric_limits<std::int32_t>::max)());
    return {compact ? GameSm3ConnectedSubmissionMode::compact_indexed :
                      GameSm3ConnectedSubmissionMode::per_instance,
            compact ? 1u : instanceCount};
}
// Large authentic D3D9 connected streams can be uploaded in multiple native
// vertex chunks. Lower EACH chunk to one indexed LINELIST/TRIANGLELIST draw,
// preserving per-instance strip/fan boundaries and alternating strip winding.
// The original game Draw remains the fallback if a whole chunk cannot fit
// the existing bounded index buffer.
struct GameSm3SegmentedConnectedSubmission {
    bool grouped = false;
    std::uint32_t batches = 0u;
};
[[nodiscard]] constexpr GameSm3SegmentedConnectedSubmission
game_sm3_segmented_connected_submission_plan(
    std::uint32_t primitiveType, bool pointFill, bool wireFill,
    std::uint32_t sourceCount, std::uint32_t verticesPerInstance,
    std::uint32_t instanceCount, std::uint32_t instancesPerUpload,
    std::uint32_t maxIndices) noexcept {
    const bool line = primitiveType == 3u;
    // D3D9 POINT and WIREFRAME triangle strips/fans have exactly the
    // same authentic ordered triangle corners as SOLID. Expand them to
    // bounded per-instance triangle lists, then submit the generated IB
    // with the already admitted POINTLIST or wireframe rasterizer.
    // LINESTRIP has no triangle polygon fill and must remain unmodified.
    if ((!line && primitiveType != 5u && primitiveType != 6u) ||
        (line && (pointFill || wireFill)) || (pointFill && wireFill) ||
        !verticesPerInstance ||
        sourceCount < (line ? 2u : 3u) ||
        instancesPerUpload < 2u || instanceCount <= instancesPerUpload ||
        !maxIndices) return {};
    const std::uint64_t perInstance =
        (std::uint64_t(sourceCount) - (line ? 1u : 2u)) *
        (line ? 2u : 3u);
    constexpr std::uint64_t kMaxTempIndices =
        (1ull << 25u) / sizeof(std::uint32_t);
    const std::uint64_t limit = (std::min)(
        std::uint64_t(maxIndices), kMaxTempIndices);
    if (perInstance > limit / instancesPerUpload ||
        std::uint64_t(verticesPerInstance) * instancesPerUpload >
            std::uint64_t((std::numeric_limits<std::int32_t>::max)()))
        return {};
    return {true, static_cast<std::uint32_t>(
        (std::uint64_t(instanceCount) + instancesPerUpload - 1u) /
        instancesPerUpload)};
}
} // namespace outrun::vr::dx11::live_game_frame
