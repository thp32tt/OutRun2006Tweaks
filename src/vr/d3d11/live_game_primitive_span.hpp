#pragma once

#include <algorithm>
#include <cstdint>
#include <vector>

namespace outrun::vr::dx11::live_game_frame {
// A complete D3D9 DrawIndexedPrimitive TRIANGLELIST can reference up to
// 512 * 3 distinct vertices. Bound the live sparse capture to that same
// 1536-element native Draw input limit (not the former 128-vertex probe cap).
inline constexpr std::uint32_t kMaxNativeGameVertices = 1536u;
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
 
// D3DPRIMITIVETYPE values (1..6) are defined by D3D9. Keep this span
// validator independent of Windows headers for deterministic Linux probes.
constexpr bool game_native_primitive_element_count(
    std::uint32_t d3d9Type, std::uint32_t primitiveCount,
    std::uint32_t& elements) noexcept {
    switch (d3d9Type) {
    case 1u: // D3DPT_POINTLIST: one source vertex per point
        if (primitiveCount == 0u || primitiveCount > 512u) return false;
        elements = primitiveCount;
        return true;
    case 2u: // D3DPT_LINELIST: P * 2 source elements
    case 3u: { // D3DPT_LINESTRIP: P + 1 source elements
        if (primitiveCount == 0u || primitiveCount > 512u) return false;
        const std::uint64_t required = d3d9Type == 2u
            ? static_cast<std::uint64_t>(primitiveCount) * 2u
            : static_cast<std::uint64_t>(primitiveCount) + 1u;
        if (required > 1536u) return false;
        elements = static_cast<std::uint32_t>(required);
        return true;
    }
    case 4u: return game_primitive_element_count(false, primitiveCount, elements); // TRIANGLELIST
    case 5u: // TRIANGLESTRIP
    case 6u: return game_primitive_element_count(true, primitiveCount, elements); // TRIANGLEFAN
    default: return false; // Unknown primitive modes remain DX9Ex-only.
    }
}

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
