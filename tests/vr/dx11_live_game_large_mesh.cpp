// Bounded game-native geometry regression: original D3D9 input/Draw remains authoritative.
// Standalone: c++ -std=c++17 -Isrc tests/vr/dx11_live_game_large_mesh.cpp -o /tmp/dx11-large-mesh && /tmp/dx11-large-mesh
#include "vr/d3d11/live_game_primitive_span.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    std::uint32_t count = 0u;
    for (std::uint32_t type = 1u; type <= 6u; ++type) {
        assert(game_native_primitive_element_count(type, kMaxNativeGamePrimitives, count));
        assert(count <= kMaxNativeGameVertices);
        assert(!game_native_primitive_element_count(type, kMaxNativeGamePrimitives + 1u, count));
        assert(!game_native_primitive_element_count(type, 0u, count));
    }
    assert(!game_native_primitive_element_count(7u, 1u, count));
    assert(game_native_primitive_element_count(4u, kMaxNativeGamePrimitives, count));
    assert(count == 6144u);
    std::vector<std::uint32_t> physical(kMaxNativeGameVertices);
    for (std::uint32_t i = 0u; i < physical.size(); ++i) physical[i] = i * 2u;
    std::vector<std::uint32_t> unique, compact;
    assert(game_compact_sparse_indices(physical.data(), static_cast<std::uint32_t>(physical.size()),
                                       kMaxNativeGameVertices, unique, compact));
    assert(unique.size() == kMaxNativeGameVertices && compact.size() == physical.size());
    assert(compact.front() == 0u && compact.back() == kMaxNativeGameVertices - 1u);
    const auto oldUnique = unique, oldCompact = compact;
    std::vector<std::uint32_t> oversized(kMaxNativeGameVertices + 1u, 1u);
    assert(!game_compact_sparse_indices(oversized.data(),
                                       static_cast<std::uint32_t>(oversized.size()),
                                       kMaxNativeGameVertices, unique, compact));
    assert(unique == oldUnique && compact == oldCompact);
    std::vector<std::uint32_t> triangles;
    assert(game_fan_to_triangle_list(kMaxNativeGamePrimitives, nullptr, 0u,
                                    kMaxNativeGamePrimitives + 2u, triangles));
    assert(triangles.size() == kMaxNativeGameVertices);
    assert(triangles[0] == 0u && triangles[1] == 1u && triangles[2] == 2u);
    assert(triangles.back() == kMaxNativeGamePrimitives + 1u);
    const auto oldTriangles = triangles;
    std::vector<std::uint32_t> badFan(kMaxNativeGamePrimitives + 2u, 0u);
    badFan.back() = kMaxNativeGameVertices + 1u;
    assert(!game_fan_to_triangle_list(kMaxNativeGamePrimitives,
                                     badFan.data(), static_cast<std::uint32_t>(badFan.size()),
                                     kMaxNativeGamePrimitives + 2u, triangles));
    assert(triangles == oldTriangles);
    assert(!game_fan_to_triangle_list(kMaxNativeGamePrimitives + 1u, nullptr, 0u,
                                     kMaxNativeGamePrimitives + 3u, triangles));
    assert(triangles == oldTriangles);
}
