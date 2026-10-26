// Actual game-authored SM3 indexed/linear polygon meshes, grouped across
// bounded native FLOAT4 instancing uploads (without merging triangle seams).
// Standalone: c++ -std=c++17 -Isrc tests/vr/dx11_live_game_segmented_polygon_fill.cpp -o /tmp/dx11-poly-fill && /tmp/dx11-poly-fill
#include "vr/d3d11/live_game_sm3_instance_batches.hpp"
#include "vr/d3d11/live_game_sm3_connected_submission.hpp"
#include "vr/d3d11/live_game_sm3_connected_instances.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    // An original indexed or nonindexed TRIANGLELIST point fill is already
    // a GPU point-occurrence IB; copy it with a per-instance vertex base.
    const auto list = game_sm3_segmented_list_submission_plan(
        4u, true, true, 8u, 3u, 6u, 64u);
    assert(list.grouped && list.batches == 3u);
    assert(!game_sm3_segmented_list_submission_plan(
        4u, false, true, 8u, 3u, 6u, 64u).grouped);
    assert(!game_sm3_segmented_list_submission_plan(
        2u, true, true, 8u, 3u, 6u, 64u).grouped);
    assert(!game_sm3_segmented_list_submission_plan(
        4u, true, true, 8u, 3u, 6u, 17u).grouped);
    std::vector<std::uint32_t> points;
    const std::uint32_t originalCorners[] = {2u, 0u, 3u, 1u, 2u, 0u};
    assert(game_sm3_expand_list_instance_indices(
        originalCorners, 6u, 5u, 3u, points));
    assert((points == std::vector<std::uint32_t>{
        2u,0u,3u,1u,2u,0u, 7u,5u,8u,6u,7u,5u,
        12u,10u,13u,11u,12u,10u}));

    // Original D3D9 point/wire strips and fans are independent triangles,
    // each retaining source index order and per-instance winding.
    const auto stripPoint = game_sm3_segmented_connected_submission_plan(
        5u, true, false, 5u, 6u, 8u, 3u, 64u);
    const auto stripWire = game_sm3_segmented_connected_submission_plan(
        5u, false, true, 5u, 6u, 8u, 3u, 64u);
    const auto fanPoint = game_sm3_segmented_connected_submission_plan(
        6u, true, false, 5u, 6u, 8u, 3u, 64u);
    const auto fanWire = game_sm3_segmented_connected_submission_plan(
        6u, false, true, 5u, 6u, 8u, 3u, 64u);
    assert(stripPoint.grouped && stripPoint.batches == 3u);
    assert(stripWire.grouped && stripWire.batches == 3u);
    assert(fanPoint.grouped && fanPoint.batches == 3u);
    assert(fanWire.grouped && fanWire.batches == 3u);
    assert(!game_sm3_segmented_connected_submission_plan(
        3u, true, false, 5u, 6u, 8u, 3u, 64u).grouped);
    assert(!game_sm3_segmented_connected_submission_plan(
        3u, false, true, 5u, 6u, 8u, 3u, 64u).grouped);
    assert(!game_sm3_segmented_connected_submission_plan(
        5u, true, false, 5u, 6u, 8u, 3u, 26u).grouped);
    assert(!game_sm3_segmented_connected_submission_plan(
        6u, false, true, 5u, 6u, 3u, 3u, 64u).grouped);

    const std::uint32_t stripIndices[] = {0u,2u,1u,4u,3u};
    std::vector<std::uint32_t> connected;
    assert(game_sm3_expand_connected_instance_indices(
        5u, stripIndices, 5u, 6u, 3u, 64u, connected));
    assert(connected.size() == 27u);
    assert((std::vector<std::uint32_t>(connected.begin(), connected.begin()+9) ==
        std::vector<std::uint32_t>{0u,2u,1u,1u,2u,4u,1u,4u,3u}));
    assert(connected[9] == 6u && connected[10] == 8u && connected[11] == 7u);
    assert(connected[18] == 12u && connected[20] == 13u);
    const std::uint32_t fanIndices[] = {0u,3u,1u,4u,2u};
    assert(game_sm3_expand_connected_instance_indices(
        6u, fanIndices, 5u, 6u, 2u, 64u, connected));
    assert((std::vector<std::uint32_t>(connected.begin(),connected.begin()+9) ==
        std::vector<std::uint32_t>{0u,3u,1u,0u,1u,4u,0u,4u,2u}));
    const auto saved = connected;
    const std::uint32_t lateBad[] = {0u,3u,1u,4u,6u};
    assert(!game_sm3_expand_connected_instance_indices(
        6u, lateBad, 5u, 6u, 2u, 64u, connected));
    assert(connected == saved); // no partial upload after late invalid IB
}
