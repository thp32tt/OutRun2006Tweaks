// 01080: genuine SM3 game-instanced list triangles/lines/points are batched
// by actual 32 MiB native GPU upload, without merging strip/fan boundaries.
#include "live_game_sm3_instance_batches.hpp"
#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;

constexpr std::uint32_t kVertices = 3840u; // divisible by triangle group
constexpr std::uint32_t kInstances = 192u;
constexpr auto kChunk = game_sm3_plan_native_instance_chunk(
    kVertices, kInstances, 64u, 1000000u, 1u << 25u);
static_assert(kChunk.instancesPerChunk > 1u &&
              kChunk.instancesPerChunk < kInstances);
constexpr auto kLinear = game_sm3_segmented_list_submission_plan(
    4u, false, false, kInstances, kChunk.instancesPerChunk, 0u, 1000000u);
constexpr auto kIndexed = game_sm3_segmented_list_submission_plan(
    4u, true, false, kInstances, kChunk.instancesPerChunk, 6u, 1000000u);
static_assert(kLinear.grouped && kLinear.batches == 2u);
static_assert(kIndexed.grouped && kIndexed.batches == 2u);
static_assert(!game_sm3_segmented_list_submission_plan(
    5u, false, false, kInstances, kChunk.instancesPerChunk, 0u, 1000000u).grouped);
static_assert(!game_sm3_segmented_list_submission_plan(
    6u, true, false, kInstances, kChunk.instancesPerChunk, 6u, 1000000u).grouped);
// A validated source TRIANGLELIST point-fill IB is the same exact
// point-occurrence stream in each bounded native instance batch.
static_assert(game_sm3_segmented_list_submission_plan(
    4u, true, true, kInstances, kChunk.instancesPerChunk, 6u, 1000000u).grouped);
static_assert(!game_sm3_segmented_list_submission_plan(
    4u, false, true, kInstances, kChunk.instancesPerChunk, 0u, 1000000u).grouped);
static_assert(!game_sm3_segmented_list_submission_plan(
    2u, true, true, kInstances, kChunk.instancesPerChunk, 6u, 1000000u).grouped);
static_assert(!game_sm3_segmented_list_submission_plan(
    4u, true, false, kInstances, kChunk.instancesPerChunk, 90000u, 1000000u).grouped);
static_assert(!game_sm3_segmented_list_submission_plan(
    4u, false, false, kInstances, 1u, 0u, 1000000u).grouped);
static_assert(!game_sm3_segmented_list_submission_plan(
    4u, false, false, 0xffffffffu, 0xffffffffu, 0u, 1000000u).grouped);

int main() {
    // An indexed triangular mesh repeats original local indices at each
    // absolute game instance; each upload starts its own GPU index offset.
    const std::array<std::uint32_t, 6> local{{0u,1u,2u,2u,1u,3u}};
    std::vector<std::uint32_t> out;
    assert(game_sm3_expand_list_instance_indices(
        local.data(), static_cast<std::uint32_t>(local.size()),
        kVertices, kChunk.instancesPerChunk, out));
    assert(out.size() == local.size() * kChunk.instancesPerChunk);
    for (std::size_t inst=0u; inst<kChunk.instancesPerChunk; ++inst)
        for (std::size_t j=0u; j<local.size(); ++j)
            assert(out[inst*local.size()+j] == inst*kVertices+local[j]);
    // A second/partial chunk starts at local vertex zero and uses precisely
    // the original D3D9 source instances still remaining.
    const auto secondCount = kInstances-kChunk.instancesPerChunk;
    assert(secondCount > 1u);
    assert(game_sm3_expand_list_instance_indices(
        local.data(), static_cast<std::uint32_t>(local.size()),
        kVertices, secondCount, out));
    assert(out[0] == 0u && out[local.size()] == kVertices);
    const auto prior = out;
    const std::array<std::uint32_t,3> invalid{{0u,1u,kVertices}};
    assert(!game_sm3_expand_list_instance_indices(
        invalid.data(), 3u, kVertices, secondCount, out));
    assert(out == prior); // D3D9 fallback retains previous source buffers
}
