#pragma once
// Original D3D9 SM3 declaration streams, already shadowed in one physical
// index order, become a single shader-visible D3D11 FLOAT4 vertex stream.
#include "live_game_sm3_vertex_unpack.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>
namespace outrun::vr::dx11::live_game_frame {
enum class GameSm3NativeUploadMode : std::uint8_t {
    invalid, flat, segmented
};
struct GameSm3NativeUploadPlan {
    GameSm3NativeUploadMode mode = GameSm3NativeUploadMode::invalid;
    std::uint32_t vertexBytes = 0u;
};
// A genuine D3D9 instanced Draw can fit the vertex COUNT limit yet exceed
// the D3D11 dynamic GPU upload BYTE limit after FLOAT4 declaration packing.
// Reuse the original per-instance vertex/IB and shader submit path instead
// of rejecting the whole menu/car/race draw or allocating an unbounded VB.
[[nodiscard]] constexpr GameSm3NativeUploadPlan
game_sm3_plan_native_instance_upload(
    bool sourceInstancing, std::uint32_t vertexCount,
    std::uint32_t instanceCount, std::uint32_t nativeStride,
    std::uint32_t maxVertices, std::uint32_t maxBytes,
    std::uint32_t maxSegmentedInstances) noexcept {
    if (!vertexCount || !instanceCount || !nativeStride ||
        !maxVertices || !maxBytes || vertexCount > maxVertices ||
        vertexCount > maxBytes / nativeStride ||
        (!sourceInstancing && instanceCount != 1u))
        return {};
    const auto expanded = std::uint64_t(vertexCount) * instanceCount;
    const bool needsSegments = expanded > maxVertices ||
        expanded > maxBytes / nativeStride;
    if (needsSegments) {
        if (!sourceInstancing || instanceCount < 2u ||
            instanceCount > maxSegmentedInstances) return {};
        return {GameSm3NativeUploadMode::segmented,
                static_cast<std::uint32_t>(std::uint64_t(vertexCount) *
                                           nativeStride)};
    }
    return {GameSm3NativeUploadMode::flat,
            static_cast<std::uint32_t>(expanded * nativeStride)};
}
struct GameSm3StreamView {
    const std::uint8_t* data{};
    std::uint32_t stride{};
    std::uint32_t vertexCount{};
};
struct GameSm3ElementRef {
    std::uint8_t stream{};
    std::uint16_t offset{};
    std::uint8_t type{};
};
[[nodiscard]] inline bool game_sm3_assemble_streams(
    const std::vector<GameSm3ElementRef>& elements,
    const std::array<GameSm3StreamView,16>& streams,
    std::uint32_t count, std::vector<std::uint8_t>& destination) noexcept {
    constexpr std::uint64_t kMaxBytes = 1ull << 25u;
    if (elements.empty() || elements.size() > 32u || !count) return false;
    const auto nativeStride = static_cast<std::uint64_t>(elements.size()) * 16u;
    if (nativeStride * count > kMaxBytes) return false;
    for (const auto& e : elements) {
        if (e.stream >= streams.size()) return false;
        const auto& src = streams[e.stream];
        const auto width = game_sm3_decl_width(e.type);
        if (!src.data || !src.stride || src.vertexCount < count ||
            !width || static_cast<std::uint32_t>(e.offset) + width > src.stride)
            return false;
    }
    try {
        std::vector<std::uint8_t> candidate(
            static_cast<std::size_t>(nativeStride * count));
        for (std::uint32_t v = 0u; v < count; ++v)
            for (std::size_t i = 0u; i < elements.size(); ++i) {
                const auto& e = elements[i];
                const auto& src = streams[e.stream];
                std::array<float,4> decoded{};
                if (!game_sm3_unpack_attribute(e.type,
                        src.data + static_cast<std::size_t>(v) * src.stride +
                            e.offset, decoded)) return false;
                std::memcpy(candidate.data() +
                    static_cast<std::size_t>(v) * nativeStride + i * 16u,
                    decoded.data(), sizeof(decoded));
            }
        destination.swap(candidate); // no partial mesh visible on failure
        return true;
    } catch (...) { return false; }
}

// CPU flattening for authentic D3D9 SetStreamSourceFreq indexed instances.
// Stream zero advances with each vertex; an instance-rate stream advances
// once per step source instances. Unlike a single D3D11 DrawInstanced, the
// expanded vertices also support the D3D9 SM3 multi-stream packed formats
// already decoded by game_sm3_unpack_attribute. The caller must issue one
// Draw/DrawIndexed PER source instance for strip and fan topology boundaries.
// firstInstance allows bounded GPU upload segments without resetting the
// source's instance-frequency divisor or treating a later instance as zero.
[[nodiscard]] inline bool game_sm3_assemble_instanced_streams(
    const std::vector<GameSm3ElementRef>& elements,
    const std::array<GameSm3StreamView,16>& streams,
    std::uint32_t verticesPerInstance, std::uint32_t instanceCount,
    const std::array<std::uint32_t,16>& instanceStep,
    std::vector<std::uint8_t>& destination,
    std::uint32_t firstInstance = 0u) noexcept {
    constexpr std::uint64_t kMaxBytes = 1ull << 25u;
    if (elements.empty() || elements.size() > 32u ||
        !verticesPerInstance || !instanceCount || instanceStep[0] != 0u ||
        firstInstance > UINT32_MAX - (instanceCount - 1u))
        return false;
    const auto stride = static_cast<std::uint64_t>(elements.size()) * 16u;
    const auto outputCount =
        static_cast<std::uint64_t>(verticesPerInstance) * instanceCount;
    if (!outputCount || outputCount > kMaxBytes / stride) return false;
    for (const auto& element : elements) {
        if (element.stream >= streams.size()) return false;
        const auto& stream = streams[element.stream];
        const auto width = game_sm3_decl_width(element.type);
        // The partial segment uses the *original* global D3D9 instance
        // ordinal; stream divisors must not restart at each GPU upload.
        const std::uint64_t lastInstance =
            std::uint64_t(firstInstance) + instanceCount - 1u;
        const std::uint64_t required = instanceStep[element.stream]
            ? lastInstance / instanceStep[element.stream] + 1u
            : verticesPerInstance;
        if (!stream.data || !stream.stride || !width ||
            stream.vertexCount < required ||
            static_cast<std::uint32_t>(element.offset) + width > stream.stride)
            return false;
    }
    try {
        std::vector<std::uint8_t> candidate(
            static_cast<std::size_t>(stride * outputCount));
        for (std::uint32_t inst = 0u; inst < instanceCount; ++inst)
            for (std::uint32_t vertex = 0u; vertex < verticesPerInstance; ++vertex)
                for (std::size_t elementIndex = 0u;
                     elementIndex < elements.size(); ++elementIndex) {
                    const auto& element = elements[elementIndex];
                    const auto& stream = streams[element.stream];
                    const auto sourceIndex = instanceStep[element.stream]
                        ? (firstInstance + inst) / instanceStep[element.stream]
                        : vertex;
                    std::array<float,4> decoded{};
                    if (!game_sm3_unpack_attribute(
                            element.type,
                            stream.data +
                                static_cast<std::size_t>(sourceIndex) * stream.stride +
                                element.offset, decoded)) return false;
                    const auto outputIndex =
                        static_cast<std::uint64_t>(inst) * verticesPerInstance +
                        vertex;
                    std::memcpy(candidate.data() +
                        static_cast<std::size_t>(outputIndex * stride +
                                                 elementIndex * 16u),
                        decoded.data(), sizeof(decoded));
                }
        destination.swap(candidate);
        return true;
    } catch (...) { return false; }
}
} // namespace outrun::vr::dx11::live_game_frame
