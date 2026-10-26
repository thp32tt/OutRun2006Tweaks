// Native shader-bound game point/line draws can inherit polygon fill mode.
#include "vr/d3d11/live_game_sm3_polygon_raster.hpp"
#include "vr/d3d11/live_game_sm3_connected_instances.hpp"
#include "vr/d3d11/live_game_sm3_instance_batches.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    for (std::uint32_t primitive : {1u, 2u, 3u})
        for (std::uint32_t fill : {1u, 2u, 3u}) {
            auto mode = game_sm3_effective_polygon_mode(fill, primitive);
            assert(mode.admitted && !mode.pointTriangles && !mode.wireTriangles);
        }
    for (std::uint32_t primitive : {4u, 5u, 6u}) {
        auto point = game_sm3_effective_polygon_mode(1u, primitive);
        auto wire = game_sm3_effective_polygon_mode(2u, primitive);
        auto solid = game_sm3_effective_polygon_mode(3u, primitive);
        assert(point.admitted && point.pointTriangles && !point.wireTriangles);
        assert(wire.admitted && wire.wireTriangles && !wire.pointTriangles);
        assert(solid.admitted && !solid.pointTriangles && !solid.wireTriangles);
        assert(!game_sm3_polygon_fill_admitted(
            1u, primitive, 2u, false, false, false)); // still cull-safe
        assert(!game_sm3_polygon_fill_admitted(
            2u, primitive, 1u, true, true, false)); // still line-AA-safe
    }
    for (std::uint32_t bad : {0u, 4u, 0xffffffffu}) {
        assert(!game_sm3_effective_polygon_mode(bad, 2u).admitted);
        assert(!game_sm3_effective_polygon_mode(2u, bad).admitted);
    }
    // An authentic indexed LINESTRIP across D3D9 instances remains
    // three independent GPU LINELIST groups regardless of inherited FILL.
    const std::uint32_t source[] = {3u, 1u, 4u, 0u};
    std::vector<std::uint32_t> native;
    assert(game_sm3_expand_connected_instance_indices(
        3u, source, 4u, 5u, 3u, 64u, native));
    assert((native == std::vector<std::uint32_t>{
        3u,1u,1u,4u,4u,0u, 8u,6u,6u,9u,9u,5u,
        13u,11u,11u,14u,14u,10u}));
    auto saved = native;
    const std::uint32_t lateBad[] = {3u, 1u, 4u, 5u};
    assert(!game_sm3_expand_connected_instance_indices(
        3u, lateBad, 4u, 5u, 3u, 64u, native));
    assert(native == saved);
    const auto pointList = game_sm3_list_submission_plan(
        1u, true, 6u, 5u, 3u, 64u);
    const auto lineList = game_sm3_list_submission_plan(
        2u, true, 6u, 5u, 3u, 64u);
    assert(pointList.mode == GameSm3ListSubmissionMode::compact_indexed);
    assert(lineList.mode == GameSm3ListSubmissionMode::compact_indexed);
}
