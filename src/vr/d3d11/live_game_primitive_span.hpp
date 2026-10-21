#pragma once

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <limits>
#include <vector>
#include "live_game_source_stride.hpp"

namespace outrun::vr::dx11::live_game_frame {
// Game-authored mesh snapshots can span 2048 primitives. One shared,
 // bounded 6144-element budget covers linear, indexed, sparse shadows and
 // native Draw/DrawIndexed. Original DX9Ex rendering stays authoritative.
inline constexpr std::uint32_t kMaxNativeGamePrimitives = 2048u;
inline constexpr std::uint32_t kMaxNativeGameVertices =
    kMaxNativeGamePrimitives * 3u;
// Common bound for actual D3D9 VB/IB/UP snapshots and D3D11 Draw/DrawIndexed.
// A strip has P+2 source elements; a list has P*3. Never infer either from
// the other: overreading a live game pointer could break the original draw.
constexpr bool game_primitive_element_count(bool triangleStrip,
                                             std::uint32_t primitiveCount,
                                             std::uint32_t& elements) noexcept {
    if (primitiveCount == 0u || primitiveCount > kMaxNativeGamePrimitives) return false;
    const std::uint64_t required = triangleStrip
        ? static_cast<std::uint64_t>(primitiveCount) + 2u
        : static_cast<std::uint64_t>(primitiveCount) * 3u;
    if (required > kMaxNativeGameVertices) return false;
    elements = static_cast<std::uint32_t>(required);
    return true;
}
 
// A successful zero-count Draw has no vertex or index buffer bytes to read.
// Unknown D3D9 topologies still break the native full-frame source stream.
[[nodiscard]] constexpr bool game_native_empty_primitive_type(
    std::uint32_t d3d9Type) noexcept {
    return d3d9Type >= 1u && d3d9Type <= 6u;
}

// D3DPRIMITIVETYPE values (1..6) are defined by D3D9. Keep this span
// validator independent of Windows headers for deterministic Linux probes.
constexpr bool game_native_primitive_element_count(
    std::uint32_t d3d9Type, std::uint32_t primitiveCount,
    std::uint32_t& elements) noexcept {
    switch (d3d9Type) {
    case 1u: // D3DPT_POINTLIST: one source vertex per point
        if (primitiveCount == 0u || primitiveCount > kMaxNativeGamePrimitives) return false;
        elements = primitiveCount;
        return true;
    case 2u: // D3DPT_LINELIST: P * 2 source elements
    case 3u: { // D3DPT_LINESTRIP: P + 1 source elements
        if (primitiveCount == 0u || primitiveCount > kMaxNativeGamePrimitives) return false;
        const std::uint64_t required = d3d9Type == 2u
            ? static_cast<std::uint64_t>(primitiveCount) * 2u
            : static_cast<std::uint64_t>(primitiveCount) + 1u;
        if (required > kMaxNativeGameVertices) return false;
        elements = static_cast<std::uint32_t>(required);
        return true;
    }
    case 4u: return game_primitive_element_count(false, primitiveCount, elements); // TRIANGLELIST
    case 5u: // TRIANGLESTRIP
    case 6u: return game_primitive_element_count(true, primitiveCount, elements); // TRIANGLEFAN
    default: return false; // Unknown primitive modes remain DX9Ex-only.
    }
}

// Compile-time edge coverage for the complete D3D9 primitive topology family.
constexpr bool game_native_mesh_span_contract() noexcept {
    std::uint32_t n = 0u;
    return game_native_primitive_element_count(1u, kMaxNativeGamePrimitives, n) &&
           n == kMaxNativeGamePrimitives &&
           game_native_primitive_element_count(2u, kMaxNativeGamePrimitives, n) &&
           n == 2u * kMaxNativeGamePrimitives &&
           game_native_primitive_element_count(3u, kMaxNativeGamePrimitives, n) &&
           n == kMaxNativeGamePrimitives + 1u &&
           game_native_primitive_element_count(4u, kMaxNativeGamePrimitives, n) &&
           n == kMaxNativeGameVertices &&
           game_native_primitive_element_count(5u, kMaxNativeGamePrimitives, n) &&
           n == kMaxNativeGamePrimitives + 2u &&
           game_native_primitive_element_count(6u, kMaxNativeGamePrimitives, n) &&
           n == kMaxNativeGamePrimitives + 2u &&
           !game_native_primitive_element_count(4u, kMaxNativeGamePrimitives + 1u, n) &&
           !game_native_primitive_element_count(6u, 0u, n);
}
static_assert(game_native_mesh_span_contract(), "Native mesh budget contract");

// Retry only when the original physical IB window was valid and the dense
// epoch-checked VB copy did not yield a native vertex span. A fragmented
// dynamic VB can have valid referenced slots separated by invalid holes.
// This decision is shared by both R30 source paths; invalid IBs never retry.
constexpr bool game_sparse_shadow_retry_eligible(
    bool physicalIndicesValid, std::uint32_t denseVertexCount) noexcept {
    return physicalIndicesValid && denseVertexCount == 0u;
}

// D3D9 can reference a few distant VB vertices in one DrawIndexedPrimitive.
// A contiguous [min,max] shadow would overread or reject that real game draw.
// Compact only the referenced *physical* VB slots, retaining original index order.
// The caller validates every indexed VB byte against its current Lock/Unlock
// shadow epoch before issuing the native DrawIndexed. Transactional on failure.
inline bool game_compact_sparse_indices(
    const std::uint32_t* physicalIndices, std::uint32_t count,
    std::uint32_t maxUnique, std::vector<std::uint32_t>& uniquePhysical,
    std::vector<std::uint32_t>& compactIndices) {
    if (!physicalIndices || count == 0u || count > kMaxNativeGameVertices ||
        maxUnique == 0u || maxUnique > kMaxNativeGameVertices) return false;
    std::vector<std::uint32_t> sorted(physicalIndices, physicalIndices + count);
    std::sort(sorted.begin(), sorted.end());
    sorted.erase(std::unique(sorted.begin(), sorted.end()), sorted.end());
    if (sorted.size() > maxUnique) return false;
    std::vector<std::uint32_t> remapped;
    remapped.reserve(count);
    for (std::uint32_t n = 0; n < count; ++n) {
        const auto found = std::lower_bound(
            sorted.begin(), sorted.end(), physicalIndices[n]);
        remapped.push_back(static_cast<std::uint32_t>(found - sorted.begin()));
    }
    uniquePhysical.swap(sorted);
    compactIndices.swap(remapped);
    return true;
}

 // DX11 real game IndexedUP: a large absolute D3D9 source vertex window can
 // contain only a handful of referenced vertices. Capture only those source
 // bytes before the UP pointers expire, preserving source index winding.
 inline bool game_gather_indexed_up_vertices(
     const void* vertexBase, std::uint32_t stride,
     const std::uint32_t* absoluteIndices, std::uint32_t indexCount,
     std::uint32_t minVertex, std::uint32_t numVertices,
     std::vector<std::uint8_t>& packedVertices,
     std::vector<std::uint32_t>& packedIndices) {
     if (!vertexBase || !absoluteIndices || !numVertices ||
         !game_native_source_stride_valid(stride) || !indexCount ||
         indexCount > kMaxNativeGameVertices ||
         minVertex > (std::numeric_limits<std::uint32_t>::max)() - numVertices)
         return false;
     for (std::uint32_t i = 0; i < indexCount; ++i) {
         if (absoluteIndices[i] < minVertex ||
             absoluteIndices[i] - minVertex >= numVertices)
             return false;
     }
     std::vector<std::uint32_t> physical, remapped;
     if (!game_compact_sparse_indices(
             absoluteIndices, indexCount, kMaxNativeGameVertices,
             physical, remapped))
         return false;
     const auto base = reinterpret_cast<std::uintptr_t>(vertexBase);
     const auto available = (std::numeric_limits<std::uintptr_t>::max)() - base;
     // No UP pointer wrap, including the last byte of every referenced vertex.
     // The original D3D9 game caller owns source readability.
     for (const auto index : physical) {
         const std::uint64_t offset = static_cast<std::uint64_t>(index) * stride;
         if (offset > available || stride > available - offset)
             return false;
     }
     std::vector<std::uint8_t> vertices(
         physical.size() * static_cast<std::size_t>(stride));
     for (std::size_t i = 0; i < physical.size(); ++i) {
         const auto offset = static_cast<std::uintptr_t>(
             static_cast<std::uint64_t>(physical[i]) * stride);
         std::memcpy(vertices.data() + i * stride,
                     reinterpret_cast<const void*>(base + offset), stride);
     }
     packedVertices.swap(vertices);
     packedIndices.swap(remapped);
     return true;
 }

// IndexedUP stream 0 comes from the call's user pointer while any referenced
// secondary streams still belong to the game's D3D9 stream bindings. Reconstruct
// the SAME physical slots in exactly the same native IA order, not the rebased
// index values. A bad index/window or a sparse compaction mismatch must abort
// before any secondary VB bytes are copied or native GPU work is queued.
// On failure preserve the previous vector; D3D9 Draw remains authoritative.
inline bool game_indexed_up_physical_slots(
    const std::uint32_t* absoluteIndices, std::uint32_t indexCount,
    std::uint32_t minVertex, std::uint32_t numVertices,
    const std::vector<std::uint32_t>& rebasedIndices, bool sparse,
    std::vector<std::uint32_t>& physical) {
    if (!absoluteIndices || indexCount == 0u ||
        indexCount > kMaxNativeGameVertices || numVertices == 0u ||
        minVertex > (std::numeric_limits<std::uint32_t>::max)() - numVertices ||
        rebasedIndices.size() != indexCount)
        return false;
    for (std::uint32_t i = 0u; i < indexCount; ++i)
        if (absoluteIndices[i] < minVertex ||
            absoluteIndices[i] - minVertex >= numVertices)
            return false;
    std::vector<std::uint32_t> slots, checked;
    if (sparse) {
        if (!game_compact_sparse_indices(absoluteIndices, indexCount,
                                         kMaxNativeGameVertices, slots, checked) ||
            checked != rebasedIndices)
            return false;
    } else {
        if (numVertices > kMaxNativeGameVertices) return false;
        for (std::uint32_t i = 0u; i < indexCount; ++i)
            if (rebasedIndices[i] != absoluteIndices[i] - minVertex)
                return false;
        slots.resize(numVertices);
        for (std::uint32_t i = 0u; i < numVertices; ++i)
            slots[i] = minVertex + i;
    }
    physical.swap(slots);
    return true;
}

// D3D9 single-sample line raster parity for *programmable* VS/PS draws.
 // The fixed-function game raster already uses these same exclusions.
 // A rejected raster never mutates the native color/depth output; original
 // D3D9 remains the only source of menu/race pixels and gamepad behavior.
[[nodiscard]] constexpr bool game_native_sm3_line_raster(
    std::uint32_t d3d9Type, bool antialiased, bool lastPixel) noexcept {
    return (d3d9Type == 2u || d3d9Type == 3u) &&
           !antialiased && lastPixel;
}
static_assert(game_native_sm3_line_raster(2u, false, true) &&
              game_native_sm3_line_raster(3u, false, true) &&
              !game_native_sm3_line_raster(2u, true, true) &&
              !game_native_sm3_line_raster(3u, false, false) &&
              !game_native_sm3_line_raster(4u, false, true));

// D3D11 draws 1-pixel points, but D3D9 may enlarge each point, scale it,
// use per-vertex PSIZE or expand texture coordinates as point sprites.
 // Only the exact unscaled singleton form is sampled into the opt-in inset.
 // IEEE754 positive finite float bit ordering permits these bounds without
 // a Windows header or introducing a floating-point failure mode.
constexpr bool game_native_unit_point_raster(
    std::uint32_t sizeBits, std::uint32_t minBits, std::uint32_t maxBits,
    std::uint32_t spriteEnabled, std::uint32_t scaleEnabled,
    bool perVertexPointSize) noexcept {
    constexpr std::uint32_t one = 0x3f800000u;
    return !perVertexPointSize && sizeBits == one &&
           minBits <= one && maxBits >= one && maxBits < 0x7f800000u &&
           spriteEnabled == 0u && scaleEnabled == 0u;
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
        vertexCount == 0u || vertexCount > kMaxNativeGameVertices) return false;
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
