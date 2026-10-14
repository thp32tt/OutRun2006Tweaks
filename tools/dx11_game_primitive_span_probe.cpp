#include "../src/vr/d3d11/live_game_primitive_span.hpp"
#include <cassert>
#include <cstdint>
#include <vector>

int main() {
    using outrun::vr::dx11::live_game_frame::game_primitive_element_count;
    using outrun::vr::dx11::live_game_frame::kMaxNativeGamePrimitives;
    using outrun::vr::dx11::live_game_frame::kMaxNativeGameVertices;
    static_assert(kMaxNativeGamePrimitives == 2048u);
    static_assert(kMaxNativeGameVertices == kMaxNativeGamePrimitives * 3u);
    std::uint32_t elements = 0xdeadbeefu;
    assert(game_primitive_element_count(false, 1, elements) && elements == 3);
    assert(game_primitive_element_count(true, 1, elements) && elements == 3);
    assert(game_primitive_element_count(false, 2, elements) && elements == 6);
    assert(game_primitive_element_count(true, 2, elements) && elements == 4);
    assert(game_primitive_element_count(false, 512, elements) && elements == 1536);
    assert(game_primitive_element_count(true, 512, elements) && elements == 514);
    assert(game_primitive_element_count(false, kMaxNativeGamePrimitives, elements) &&
           elements == kMaxNativeGameVertices);
    assert(game_primitive_element_count(true, kMaxNativeGamePrimitives, elements) &&
           elements == kMaxNativeGamePrimitives + 2u);
    const auto last = elements;
    assert(!game_primitive_element_count(false, 0, elements) && elements == last);
    assert(!game_primitive_element_count(true, 0, elements) && elements == last);
    assert(!game_primitive_element_count(false, kMaxNativeGamePrimitives + 1u, elements) && elements == last);
    assert(!game_primitive_element_count(true, kMaxNativeGamePrimitives + 1u, elements) && elements == last);
    using outrun::vr::dx11::live_game_frame::game_native_primitive_element_count;
    assert(game_native_primitive_element_count(1, 1, elements) && elements == 1);
    assert(game_native_primitive_element_count(1, 512, elements) && elements == 512);
    assert(game_native_primitive_element_count(2, 1, elements) && elements == 2);
    assert(game_native_primitive_element_count(3, 1, elements) && elements == 2);
    assert(game_native_primitive_element_count(2, 512, elements) && elements == 1024);
    assert(game_native_primitive_element_count(3, 512, elements) && elements == 513);
    assert(game_native_primitive_element_count(4, 512, elements) && elements == 1536);
    assert(game_native_primitive_element_count(5, 512, elements) && elements == 514);
    assert(game_native_primitive_element_count(6, 512, elements) && elements == 514);
    for (unsigned kind : {1u, 2u, 3u, 4u, 5u, 6u}) {
        assert(game_native_primitive_element_count(kind, kMaxNativeGamePrimitives, elements));
        assert(elements <= kMaxNativeGameVertices);
    }
    const auto retained = elements;
    for (unsigned rejected : {0u, 7u, 0xffffffffu})
        assert(!game_native_primitive_element_count(rejected, 1, elements) &&
               elements == retained);
    for (unsigned kind : {1u, 2u, 3u, 4u, 5u, 6u}) {
        assert(!game_native_primitive_element_count(kind, 0, elements) &&
               elements == retained);
        assert(!game_native_primitive_element_count(kind, kMaxNativeGamePrimitives + 1u, elements) &&
               elements == retained);
    }
    using outrun::vr::dx11::live_game_frame::game_native_unit_point_raster;
    constexpr unsigned one = 0x3f800000u;
    constexpr unsigned zero = 0u;
    constexpr unsigned maximum = 0x42800000u;
    assert(game_native_unit_point_raster(one, zero, maximum, 0, 0, false));
    assert(!game_native_unit_point_raster(one, zero, maximum, 1, 0, false));
    assert(!game_native_unit_point_raster(one, zero, maximum, 0, 1, false));
    assert(!game_native_unit_point_raster(one, zero, maximum, 0, 0, true));
    assert(!game_native_unit_point_raster(0x40000000u, zero, maximum, 0, 0, false));
    assert(!game_native_unit_point_raster(one, 0x40000000u, maximum, 0, 0, false));
    assert(!game_native_unit_point_raster(one, zero, 0x3f000000u, 0, 0, false));
    assert(!game_native_unit_point_raster(one, zero, 0x7fc00000u, 0, 0, false));
    using outrun::vr::dx11::live_game_frame::game_fan_to_triangle_list;
    std::vector<std::uint32_t> fan;
    assert(game_fan_to_triangle_list(1, nullptr, 0, 3, fan));
    assert((fan == std::vector<std::uint32_t>{0, 1, 2}));
    assert(game_fan_to_triangle_list(2, nullptr, 0, 4, fan));
    assert((fan == std::vector<std::uint32_t>{0, 1, 2, 0, 2, 3}));
    const std::uint32_t indexed[] = {3, 0, 2, 1};
    assert(game_fan_to_triangle_list(2, indexed, 4, 4, fan));
    assert((fan == std::vector<std::uint32_t>{3, 0, 2, 3, 2, 1}));
    const auto preserved = fan;
    assert(!game_fan_to_triangle_list(2, indexed, 3, 4, fan) && fan == preserved);
    assert(!game_fan_to_triangle_list(2, indexed, 4, 3, fan) && fan == preserved);
    assert(!game_fan_to_triangle_list(2, nullptr, 0, 3, fan) && fan == preserved);
    assert(!game_fan_to_triangle_list(0, nullptr, 0, 0, fan) && fan == preserved);
    assert(!game_fan_to_triangle_list(kMaxNativeGamePrimitives + 1u, nullptr, 0,
                                     kMaxNativeGamePrimitives + 3u, fan) && fan == preserved);
    // Sparse real D3D9 VB uses absolute physical offsets far outside the
    // native-mesh contiguous-slot diagnostic bound, but only three distinct slots.
    using outrun::vr::dx11::live_game_frame::game_compact_sparse_indices;
    const std::uint32_t distant[] = {100u, 10000u, 100u, 200000u, 10000u};
    std::vector<std::uint32_t> uniqueSlots{999u}, remapped{888u};
    assert(game_compact_sparse_indices(distant, 5u, 3u, uniqueSlots, remapped));
    assert((uniqueSlots == std::vector<std::uint32_t>{100u, 10000u, 200000u}));
    assert((remapped == std::vector<std::uint32_t>{0u, 1u, 0u, 2u, 1u}));
    const auto keptSlots = uniqueSlots, keptIndices = remapped;
    assert(!game_compact_sparse_indices(distant, 5u, 2u, uniqueSlots, remapped));
    assert(uniqueSlots == keptSlots && remapped == keptIndices);
    assert(!game_compact_sparse_indices(nullptr, 5u, 3u, uniqueSlots, remapped));
    assert(!game_compact_sparse_indices(distant, 0u, 3u, uniqueSlots, remapped));
    assert(!game_compact_sparse_indices(distant, kMaxNativeGameVertices + 1u, 3u, uniqueSlots, remapped));
    assert(uniqueSlots == keptSlots && remapped == keptIndices);
    // A compact live draw can reference valid VB vertices across invalid
    // shadow holes: dense copy fails, then bounded sparse capture is eligible.
    using outrun::vr::dx11::live_game_frame::game_sparse_shadow_retry_eligible;
    static_assert(game_sparse_shadow_retry_eligible(true, 0u));
    static_assert(!game_sparse_shadow_retry_eligible(false, 0u));
    static_assert(!game_sparse_shadow_retry_eligible(true, 3u));
    // No data is committed on an invalid/missing sparse source.
    const auto previouslyMapped = remapped;
    assert(!game_compact_sparse_indices(nullptr, 3u, 3u,
                                       uniqueSlots, remapped));
    assert(remapped == previouslyMapped);
    // 00679: a full 2048-triangle game mesh may use 6144 non-contiguous
    // physical VB slots. Compact the real index order without reading holes.
    std::vector<std::uint32_t> fullMesh(kMaxNativeGameVertices);
    for (std::uint32_t i = 0; i < kMaxNativeGameVertices; ++i)
        fullMesh[i] = 100000u + (kMaxNativeGameVertices - 1u - i) * 7u;
    assert(game_compact_sparse_indices(
        fullMesh.data(), static_cast<std::uint32_t>(fullMesh.size()),
        kMaxNativeGameVertices, uniqueSlots, remapped));
    assert(uniqueSlots.size() == kMaxNativeGameVertices &&
           remapped.size() == kMaxNativeGameVertices);
    for (std::uint32_t i = 0; i < kMaxNativeGameVertices; ++i) {
        assert(uniqueSlots[i] == 100000u + i * 7u);
        assert(remapped[i] == kMaxNativeGameVertices - 1u - i);
    }
    // An oversubscribed request must leave the previously accepted native
    // vertex/index snapshot intact; game D3D9 Draw still owns the fallback.

    // 00737 game IndexedUP: scattered original MinVertexIndex >= 6144 is
    // compacted, never read as a dense 40k-vertex source window.
    using outrun::vr::dx11::live_game_frame::game_gather_indexed_up_vertices;
    constexpr std::uint32_t sparseStride = 16u, sparseMin = 9000u;
    std::vector<std::uint8_t> upSource(11001u * sparseStride, 0u);
    upSource[9000u * sparseStride] = 0x41u;
    upSource[10000u * sparseStride] = 0x72u;
    const std::uint32_t upIndices[] = {10000u, 9000u, 10000u};
    std::vector<std::uint8_t> upPacked{0xccu};
    std::vector<std::uint32_t> upRemapped{888u};
    assert(game_gather_indexed_up_vertices(
        upSource.data(), sparseStride, upIndices, 3u, sparseMin, 40000u,
        upPacked, upRemapped));
    assert(upPacked.size() == 2u * sparseStride &&
           upPacked[0] == 0x41u && upPacked[sparseStride] == 0x72u);
    assert((upRemapped == std::vector<std::uint32_t>{1u, 0u, 1u}));
    const auto keptUp = upPacked, keptUpIndices = upRemapped;
    const std::uint32_t badUp[] = {10000u, 8999u, 10000u};
    assert(!game_gather_indexed_up_vertices(
        upSource.data(), sparseStride, badUp, 3u, sparseMin, 40000u,
        upPacked, upRemapped));
    assert(!game_gather_indexed_up_vertices(
        upSource.data(), sparseStride, upIndices, 3u, 0xfffffffcu, 8u,
        upPacked, upRemapped));
    assert(!game_gather_indexed_up_vertices(
        nullptr, sparseStride, upIndices, 3u, sparseMin, 40000u,
        upPacked, upRemapped));
    assert(!game_gather_indexed_up_vertices(
        upSource.data(), 0u, upIndices, 3u, sparseMin, 40000u,
        upPacked, upRemapped));
    assert(!game_gather_indexed_up_vertices(
        upSource.data(), sparseStride, upIndices,
        kMaxNativeGameVertices + 1u, sparseMin, 40000u,
        upPacked, upRemapped));
    assert(upPacked == keptUp && upRemapped == keptUpIndices);
    const auto fullUnique = uniqueSlots, fullRemap = remapped;
    assert(!game_compact_sparse_indices(
        fullMesh.data(), static_cast<std::uint32_t>(fullMesh.size()),
        kMaxNativeGameVertices - 1u, uniqueSlots, remapped));
    assert(uniqueSlots == fullUnique && remapped == fullRemap);
    assert(!game_compact_sparse_indices(
        fullMesh.data(), static_cast<std::uint32_t>(fullMesh.size()),
        kMaxNativeGameVertices + 1u, uniqueSlots, remapped));
    assert(uniqueSlots == fullUnique && remapped == fullRemap);
    return 0;
}
