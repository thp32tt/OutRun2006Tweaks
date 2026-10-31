#include <cassert>
#include <cstdint>
#include <vector>
#include "vr/d3d11/live_game_sm3_polygon_raster.hpp"

// Same native polygon geometry helper drives live FVF and programmable SM3.
// FVF full-game admission additionally requires unit points/no culling and
// wireframe line AA/LASTPIXEL safety before GPU submission.
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    for (std::uint32_t inherited : {1u, 2u, 3u}) {
        for (std::uint32_t primitive : {1u, 2u, 3u}) {
            const auto mode = game_sm3_effective_polygon_mode(inherited, primitive);
            assert(mode.admitted && !mode.pointTriangles && !mode.wireTriangles);
        }
    }
    for (std::uint32_t primitive : {4u, 5u, 6u}) {
        assert(game_sm3_effective_polygon_mode(1u, primitive).pointTriangles);
        assert(game_sm3_effective_polygon_mode(2u, primitive).wireTriangles);
        assert(!game_sm3_effective_polygon_mode(3u, primitive).pointTriangles);
        assert(!game_sm3_effective_polygon_mode(3u, primitive).wireTriangles);
        assert(game_sm3_polygon_fill_admitted(1u, primitive, 1u, false, false, true));
        assert(!game_sm3_polygon_fill_admitted(1u, primitive, 2u, false, false, true));
        assert(game_sm3_polygon_fill_admitted(2u, primitive, 2u, false, true, false));
        assert(!game_sm3_polygon_fill_admitted(2u, primitive, 2u, true, true, false));
    }
    // An unindexed full-frame FVF strip must retain every triangle corner
    // including the alternating winding and shared/repeated occurrences.
    std::vector<std::uint32_t> out{99u};
    assert(game_sm3_expand_polygon_points(5u, nullptr, 5u, 5u, 64u, out));
    assert((out == std::vector<std::uint32_t>{0,1,2, 2,1,3, 2,3,4}));
    const std::uint32_t indexed[]{4,2,3,1,0};
    assert(game_sm3_expand_polygon_points(5u, indexed, 5u, 5u, 64u, out));
    assert((out == std::vector<std::uint32_t>{4,2,3, 3,2,1, 3,1,0}));
    const auto intact = out;
    assert(!game_sm3_expand_polygon_points(5u, indexed, 5u, 5u, 8u, out));
    assert(out == intact); // oversized native IB never partially mutates
    const std::uint32_t corrupt[]{4,2,9,1,0};
    assert(!game_sm3_expand_polygon_points(5u, corrupt, 5u, 5u, 64u, out));
    assert(out == intact); // bad later D3D9 index remains D3D9-owned
    assert(!game_sm3_effective_polygon_mode(0u,4u).admitted);
    assert(!game_sm3_effective_polygon_mode(2u,7u).admitted);
}
