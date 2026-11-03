#pragma once
// Original D3D9 SM3 declaration streams, already shadowed in one physical
// index order, become a single shader-visible D3D11 FLOAT4 vertex stream.
#include "live_game_sm3_vertex_unpack.hpp"
#include <algorithm>
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
// Group consecutive source-authored instances in bounded D3D11 dynamic VB
// uploads. A connected strip/fan still requires separate Draws per original
// instance; chunking only changes how often GPU storage is renamed.
// Admission uses the *actual* packed FLOAT4 IA stride, never the D3D9 stride.
struct GameSm3NativeChunkPlan {
    std::uint32_t instancesPerChunk = 0u;
    std::uint32_t firstUploadBytes = 0u;
};
[[nodiscard]] constexpr GameSm3NativeChunkPlan
game_sm3_plan_native_instance_chunk(
    std::uint32_t verticesPerInstance, std::uint32_t instanceCount,
    std::uint32_t nativeStride, std::uint32_t maxVertices,
    std::uint32_t maxBytes) noexcept {
    if (!verticesPerInstance || !instanceCount || !nativeStride ||
        !maxVertices || !maxBytes) return {};
    const std::uint64_t bytesPerInstance =
        std::uint64_t(verticesPerInstance) * nativeStride;
    if (bytesPerInstance > maxBytes || verticesPerInstance > maxVertices)
        return {};
    const std::uint64_t count = (std::min)(
        std::uint64_t(instanceCount),
        (std::min)(std::uint64_t(maxVertices / verticesPerInstance),
                   std::uint64_t(maxBytes) / bytesPerInstance));
    if (!count || count > UINT32_MAX) return {};
    return {static_cast<std::uint32_t>(count),
            static_cast<std::uint32_t>(count * bytesPerInstance)};
}
// A real, non-instanced D3D9 point/line/triangle list can be valid in the
// original source VB yet exceed the 32 MiB native FLOAT4 upload after a
// multi-stream/packed-declaration expansion. Preserve the exact primitive
// order with several bounded GPU uploads; never split a line or triangle.
// Indexed draws and connected strips/fans cannot be sliced this way.
struct GameSm3LinearChunkPlan {
    std::uint32_t verticesPerChunk = 0u;
    std::uint32_t chunkCount = 0u;
};
[[nodiscard]] constexpr GameSm3LinearChunkPlan
game_sm3_plan_native_linear_chunks(
    std::uint32_t primitiveType, bool indexed, std::uint32_t sourceVertices,
    std::uint32_t nativeStride, std::uint32_t maxVerticesPerChunk,
    std::uint32_t maxBytesPerChunk, std::uint32_t maxChunks) noexcept {
    const std::uint32_t group = primitiveType == 1u ? 1u :
                                primitiveType == 2u ? 2u :
                                primitiveType == 4u ? 3u : 0u;
    if (!group || indexed || !nativeStride || !sourceVertices ||
        sourceVertices % group != 0u || !maxChunks)
        return {};
    const std::uint32_t limit = (std::min)(
        maxVerticesPerChunk, maxBytesPerChunk / nativeStride);
    const std::uint32_t aligned = limit - limit % group;
    if (!aligned || sourceVertices <= aligned) return {};
    const std::uint64_t chunks =
        (std::uint64_t(sourceVertices) + aligned - 1u) / aligned;
    if (chunks > maxChunks) return {};
    return {aligned, static_cast<std::uint32_t>(chunks)};
}

// Indexed real-game independent lists may exceed the native 32 MiB FLOAT4
// buffer after declaration unpacking although their original D3D9 VB fits.
// Expand original index occurrences in primitive-aligned native GPU windows;
// connected topologies, source instancing and point/wire polygon fill remain
// outside the opt-in indexed streaming admission.
struct GameSm3IndexedChunkPlan {
    std::uint32_t verticesPerChunk = 0u;
    std::uint32_t chunkCount = 0u;
};
[[nodiscard]] constexpr GameSm3IndexedChunkPlan
game_sm3_plan_native_indexed_chunks(
    std::uint32_t primitiveType, std::uint32_t sourceVertices,
    std::uint32_t indexCount, std::uint32_t nativeStride,
    std::uint32_t maxVertices, std::uint32_t maxBytes,
    std::uint32_t maxChunks, std::uint64_t maxTotalBytes) noexcept {
    const std::uint32_t group = primitiveType == 1u ? 1u :
                                primitiveType == 2u ? 2u :
                                primitiveType == 4u ? 3u : 0u;
    if (!group || !sourceVertices || !indexCount || !nativeStride ||
        !maxVertices || !maxBytes || !maxChunks || indexCount % group ||
        sourceVertices > maxVertices ||
        std::uint64_t(sourceVertices) * nativeStride <= maxBytes ||
        std::uint64_t(indexCount) * nativeStride > maxTotalBytes) return {};
    const auto limit = (std::min)(maxVertices, maxBytes / nativeStride);
    const auto capacity = limit - limit % group;
    if (!capacity) return {};
    const auto chunks = (std::uint64_t(indexCount) + capacity - 1u) / capacity;
    if (chunks > maxChunks) return {};
    return {capacity, static_cast<std::uint32_t>(chunks)};
}

// A source-authored LINESTRIP or TRIANGLESTRIP is connected across all
// vertices. Native WRITE_DISCARD segments repeat the preceding 1/2 vertices
// at each boundary; for triangle strips the advance must be even so the
// rasterizer's alternating winding matches the original global strip.
// D3D9 TRIANGLEFAN and indexed strips still use the authoritative fallback.
struct GameSm3ConnectedChunkPlan {
    std::uint32_t verticesPerChunk = 0u;
    std::uint32_t advanceVertices = 0u;
    std::uint32_t chunkCount = 0u;
};
[[nodiscard]] constexpr GameSm3ConnectedChunkPlan
game_sm3_plan_native_connected_chunks(
    std::uint32_t primitiveType, bool indexed, std::uint32_t sourceVertices,
    std::uint32_t nativeStride, std::uint32_t maxVerticesPerChunk,
    std::uint32_t maxBytesPerChunk, std::uint32_t maxChunks) noexcept {
    const bool line = primitiveType == 3u;
    const bool triangle = primitiveType == 5u;
    if ((!line && !triangle) || indexed || !nativeStride ||
        !maxVerticesPerChunk || !maxBytesPerChunk || !maxChunks ||
        sourceVertices < (line ? 2u : 3u)) return {};
    std::uint32_t capacity = (std::min)(
        maxVerticesPerChunk, maxBytesPerChunk / nativeStride);
    // For a TRIANGLESTRIP every segment begins on an EVEN original
    // triangle ordinal; its first two vertices are the previous tail.
    if (triangle) capacity -= capacity % 2u;
    if (capacity < (line ? 2u : 4u) || sourceVertices <= capacity)
        return {};
    const std::uint32_t advance = capacity - (line ? 1u : 2u);
    const std::uint64_t remaining = std::uint64_t(sourceVertices) - capacity;
    const std::uint64_t chunks = 1u + (remaining + advance - 1u) / advance;
    if (chunks > maxChunks) return {};
    return {capacity, advance, static_cast<std::uint32_t>(chunks)};
}


// Real-game indexed LINESTRIP/TRIANGLESTRIP: expand source IB occurrences
// into bounded FLOAT4 native GPU stream windows. Repeat one line endpoint
// or two triangle endpoints; triangle starts advance by an EVEN ordinal
// so the native alternating winding remains identical to the source.
[[nodiscard]] constexpr GameSm3ConnectedChunkPlan
game_sm3_plan_native_indexed_connected_chunks(
    std::uint32_t primitiveType, std::uint32_t sourceVertices,
    std::uint32_t sourceIndices, std::uint32_t nativeStride,
    std::uint32_t maxVertices, std::uint32_t maxBytes,
    std::uint32_t maxChunks, std::uint64_t maxTotalBytes) noexcept {
    const bool line = primitiveType == 3u;
    if ((!line && primitiveType != 5u) || !sourceVertices ||
        sourceIndices < (line ? 3u : 4u) || !nativeStride ||
        sourceVertices > maxVertices ||
        std::uint64_t(sourceVertices) * nativeStride <= maxBytes)
        return {};
    const auto plan = game_sm3_plan_native_connected_chunks(
        primitiveType, false, sourceIndices, nativeStride,
        maxVertices, maxBytes, maxChunks);
    if (plan.chunkCount < 2u) return {};
    // GPU traffic includes each reuploaded seam. Limit both one upload
    // and total transient traffic before any native Draw is admitted.
    const std::uint64_t uploadedVertices =
        std::uint64_t(sourceIndices) +
        std::uint64_t(line ? 1u : 2u) * (plan.chunkCount - 1u);
    if (uploadedVertices > maxTotalBytes / nativeStride) return {};
    return plan;
}

 // A D3D9 nonindexed TRIANGLEFAN has a permanent center vertex (source 0).
 // Each bounded native GPU segment contains that original center plus the
 // previous rim endpoint and new rim vertices. Each native chunk gets its
 // own triangle-list IB; no D3D11 fan topology or duplicated fan triangles.
 struct GameSm3FanChunkPlan {
     std::uint32_t verticesPerChunk = 0u;
     std::uint32_t advanceRimVertices = 0u;
     std::uint32_t chunkCount = 0u;
 };
 [[nodiscard]] constexpr GameSm3FanChunkPlan game_sm3_plan_native_fan_chunks(
     std::uint32_t sourceVertices, std::uint32_t nativeStride,
     std::uint32_t maxVerticesPerChunk, std::uint32_t maxBytesPerChunk,
     std::uint32_t maxIndicesPerChunk, std::uint32_t maxChunks) noexcept {
     if (sourceVertices < 3u || !nativeStride || !maxIndicesPerChunk ||
         !maxVerticesPerChunk || !maxBytesPerChunk || !maxChunks)
         return {};
     const std::uint32_t capacity = (std::min)(
         (std::min)(maxVerticesPerChunk, maxBytesPerChunk / nativeStride),
         maxIndicesPerChunk / 3u + 2u);
     if (capacity < 3u || sourceVertices <= capacity) return {};
     const std::uint32_t advance = capacity - 2u;
     const std::uint64_t remaining = std::uint64_t(sourceVertices) - capacity;
     const std::uint64_t count = 1u + (remaining + advance - 1u) / advance;
     if (count > maxChunks) return {};
     return {capacity, advance, static_cast<std::uint32_t>(count)};
 }
// D3D9 indexed TRIANGLEFAN source indices are a center plus a connected rim.
// Build bounded shader-visible native windows from ORIGINAL index occurrences;
// full-fan triangle expansion can overflow the bounded native IB even though
// each D3D9 source index and each window is individually valid.
[[nodiscard]] constexpr GameSm3FanChunkPlan
game_sm3_plan_native_indexed_fan_chunks(
    std::uint32_t sourceVertices, std::uint32_t sourceIndices,
    std::uint32_t nativeStride, std::uint32_t maxVertices,
    std::uint32_t maxBytes, std::uint32_t maxIndices,
    std::uint32_t maxChunks, std::uint64_t maxTotalBytes) noexcept {
    if (!sourceVertices || sourceVertices > maxVertices ||
        sourceIndices < 3u || !nativeStride || !maxTotalBytes)
        return {};
    const auto plan = game_sm3_plan_native_fan_chunks(
        sourceIndices, nativeStride, maxVertices, maxBytes,
        maxIndices, maxChunks);
    if (plan.chunkCount < 2u) return {};
    // Each continuation reuploads the center and one common rim vertex.
    const std::uint64_t uploadVertices =
        std::uint64_t(sourceIndices) + 2u * (plan.chunkCount - 1u);
    if (uploadVertices > maxTotalBytes / nativeStride) return {};
    return plan;
}

 // Convert one complete center+rim GPU window to D3D11 triangle-list indices.
 [[nodiscard]] inline bool game_sm3_fan_window_indices(
     std::uint32_t vertices, std::uint32_t maxIndices,
     std::vector<std::uint32_t>& output) noexcept {
     if (vertices < 3u || vertices - 2u > maxIndices / 3u)
         return false;
     try {
         std::vector<std::uint32_t> candidate;
         candidate.reserve(static_cast<std::size_t>(vertices - 2u) * 3u);
         for (std::uint32_t i = 1u; i + 1u < vertices; ++i) {
             candidate.push_back(0u);
             candidate.push_back(i);
             candidate.push_back(i + 1u);
         }
         output.swap(candidate);
         return true;
     } catch (...) { return false; }
 }
 // Preserve original center and seam attributes for an already native-format
 // shader input stream. All failures leave the caller's previous data intact.
 [[nodiscard]] inline bool game_sm3_copy_native_fan_window(
     const std::uint8_t* source, std::uint32_t stride,
     std::uint32_t sourceVertices, std::uint32_t firstRim,
     std::uint32_t windowVertices, std::vector<std::uint8_t>& output) noexcept {
     if (!source || !stride || firstRim == 0u ||
         windowVertices < 3u || firstRim > sourceVertices ||
         windowVertices - 1u > sourceVertices - firstRim ||
         std::uint64_t(windowVertices) * stride > (1ull << 25u))
         return false;
     try {
         std::vector<std::uint8_t> candidate(
             static_cast<std::size_t>(windowVertices) * stride);
         std::memcpy(candidate.data(), source, stride);
         std::memcpy(candidate.data() + stride,
             source + static_cast<std::size_t>(firstRim) * stride,
             static_cast<std::size_t>(windowVertices - 1u) * stride);
         output.swap(candidate);
         return true;
     } catch (...) { return false; }
 }

// A high-instance-count game mesh can exceed the historical 128 native
// submissions even though its original D3D9 stream is complete and each
// packed FLOAT4 GPU chunk fits. Admit a bounded continuation without ever
// allocating all expanded instances together. Historical <=128 submits retain
// their previous admission; additional draws are limited to 256 and 64 MiB
// of total CPU-packed/GPU-streamed vertex data per source Draw.
[[nodiscard]] constexpr bool game_sm3_extended_instance_upload_allowed(
    std::uint32_t verticesPerInstance, std::uint32_t instanceCount,
    std::uint32_t nativeStride, std::uint32_t legacyDrawLimit,
    std::uint32_t extendedDrawLimit,
    std::uint64_t extraTotalByteLimit) noexcept {
    if (!verticesPerInstance || !instanceCount || !nativeStride ||
        !legacyDrawLimit || extendedDrawLimit < legacyDrawLimit)
        return false;
    if (instanceCount <= legacyDrawLimit) return true;
    // Divide before multiplying: even malicious 32-bit source counts cannot
    // wrap an allocation or turn an oversized Draw into valid geometry.
    return instanceCount <= extendedDrawLimit &&
        std::uint64_t(verticesPerInstance) * instanceCount <=
            extraTotalByteLimit / nativeStride;
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
    std::uint32_t count, std::vector<std::uint8_t>& destination,
    std::uint32_t firstVertex = 0u) noexcept {
    constexpr std::uint64_t kMaxBytes = 1ull << 25u;
    if (elements.empty() || elements.size() > 32u || !count) return false;
    const auto nativeStride = static_cast<std::uint64_t>(elements.size()) * 16u;
    if (nativeStride * count > kMaxBytes) return false;
    for (const auto& e : elements) {
        if (e.stream >= streams.size()) return false;
        const auto& src = streams[e.stream];
        const auto width = game_sm3_decl_width(e.type);
        if (!src.data || !src.stride || firstVertex > src.vertexCount ||
            count > src.vertexCount - firstVertex || !width || static_cast<std::uint32_t>(e.offset) + width > src.stride)
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
                        src.data + static_cast<std::size_t>(firstVertex + v) * src.stride +
                            e.offset, decoded)) return false;
                std::memcpy(candidate.data() +
                    static_cast<std::size_t>(v) * nativeStride + i * 16u,
                    decoded.data(), sizeof(decoded));
            }
        destination.swap(candidate); // no partial mesh visible on failure
        return true;
    } catch (...) { return false; }
}


 // Assemble actual indexed D3D9 stream attributes in exact IB occurrence order.
// All bounds are checked before staged writes; a failed source never replaces
// a previously valid native vertex window.
[[nodiscard]] inline bool game_sm3_assemble_indexed_window(
    const std::vector<GameSm3ElementRef>& elements,
    const std::array<GameSm3StreamView,16>& streams,
    const std::uint32_t* indices, std::uint32_t totalIndices,
    std::uint32_t firstIndex, std::uint32_t count,
    std::vector<std::uint8_t>& output) noexcept {
    if (!indices || elements.empty() || elements.size() > 32u ||
        !count || firstIndex > totalIndices ||
        count > totalIndices - firstIndex) return false;
    const std::uint64_t stride = std::uint64_t(elements.size()) * 16u;
    if (std::uint64_t(count) * stride > (1ull << 25u)) return false;
    for (const auto& element : elements) {
        if (element.stream >= streams.size()) return false;
        const auto& stream = streams[element.stream];
        const auto width = game_sm3_decl_width(element.type);
        if (!stream.data || !stream.stride || !width ||
            std::uint32_t(element.offset) + width > stream.stride) return false;
        for (std::uint32_t v=0u;v<count;++v)
            if (indices[firstIndex+v] >= stream.vertexCount) return false;
    }
    try {
        std::vector<std::uint8_t> staged(
            static_cast<std::size_t>(std::uint64_t(count) * stride));
        for (std::uint32_t v=0u;v<count;++v)
            for (std::size_t a=0u;a<elements.size();++a) {
                const auto& element=elements[a];
                const auto& stream=streams[element.stream];
                std::array<float,4> value{};
                if (!game_sm3_unpack_attribute(element.type,
                    stream.data + std::size_t(indices[firstIndex+v]) *
                    stream.stride + element.offset, value)) return false;
                std::memcpy(staged.data() + std::size_t(v)*stride + a*16u,
                            value.data(), sizeof(value));
            }
        output.swap(staged);
        return true;
    } catch (...) { return false; }
}

// Resolve an indexed fan's original center and rim *before* any GPU upload.
// Both packed SM3 attributes and unmodified native-format source streams
// use the same index-selection semantics, retaining repeated source indices.
[[nodiscard]] inline bool game_sm3_assemble_indexed_fan_window(
    const std::vector<GameSm3ElementRef>& elements,
    const std::array<GameSm3StreamView,16>& streams,
    const std::uint32_t* indices, std::uint32_t sourceIndices,
    std::uint32_t firstRim, std::uint32_t windowVertices,
    std::vector<std::uint8_t>& output) noexcept {
    if (!indices || !firstRim || windowVertices < 3u ||
        firstRim > sourceIndices ||
        windowVertices - 1u > sourceIndices - firstRim)
        return false;
    try {
        std::vector<std::uint32_t> selected;
        selected.reserve(windowVertices);
        selected.push_back(indices[0u]);
        for (std::uint32_t i = 1u; i < windowVertices; ++i)
            selected.push_back(indices[firstRim + i - 1u]);
        return game_sm3_assemble_indexed_window(
            elements, streams, selected.data(), windowVertices,
            0u, windowVertices, output);
    } catch (...) { return false; }
}
[[nodiscard]] inline bool game_sm3_copy_native_indexed_fan_window(
    const std::uint8_t* source, std::uint32_t stride,
    std::uint32_t sourceVertices,
    const std::uint32_t* indices, std::uint32_t sourceIndices,
    std::uint32_t firstRim, std::uint32_t windowVertices,
    std::vector<std::uint8_t>& output) noexcept {
    if (!source || !stride || !indices || !sourceVertices ||
        !firstRim || windowVertices < 3u || firstRim > sourceIndices ||
        windowVertices - 1u > sourceIndices - firstRim ||
        std::uint64_t(windowVertices) * stride > (1ull << 25u))
        return false;
    for (std::uint32_t v = 0u; v < windowVertices; ++v)
        if (indices[v ? firstRim + v - 1u : 0u] >= sourceVertices)
            return false;
    try {
        std::vector<std::uint8_t> staged(
            static_cast<std::size_t>(windowVertices) * stride);
        for (std::uint32_t v = 0u; v < windowVertices; ++v) {
            const auto sourceIndex = indices[v ? firstRim + v - 1u : 0u];
            std::memcpy(staged.data() + std::size_t(v) * stride,
                        source + std::size_t(sourceIndex) * stride, stride);
        }
        output.swap(staged);
        return true;
    } catch (...) { return false; }
}

// FLOAT4 declaration expansion for the same center+rim fan windows. Decode
 // actual source 0 once and a contiguous original rim slice; never reinterpret
 // packed D3D9 attributes or replace a seam by an adjacent shader input.
 [[nodiscard]] inline bool game_sm3_assemble_fan_window(
     const std::vector<GameSm3ElementRef>& elements,
     const std::array<GameSm3StreamView,16>& streams,
     std::uint32_t firstRim, std::uint32_t windowVertices,
     std::vector<std::uint8_t>& output) noexcept {
     if (!firstRim || windowVertices < 3u || elements.empty() ||
         elements.size() > 32u ||
         std::uint64_t(windowVertices) * elements.size() * 16u >
             (1ull << 25u)) return false;
     std::vector<std::uint8_t> center, rim;
     if (!game_sm3_assemble_streams(elements, streams, 1u, center) ||
         !game_sm3_assemble_streams(elements, streams,
                                  windowVertices - 1u, rim, firstRim))
         return false;
     try {
         std::vector<std::uint8_t> candidate;
         candidate.reserve(center.size() + rim.size());
         candidate.insert(candidate.end(), center.begin(), center.end());
         candidate.insert(candidate.end(), rim.begin(), rim.end());
         output.swap(candidate);
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
