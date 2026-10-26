#include "live_game_sm3_stream_assembly.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
constexpr std::uint32_t vertexCount = 4000u;
constexpr std::uint32_t instanceCount = 192u;
constexpr std::uint32_t stride = 64u;
constexpr auto plan = game_sm3_plan_native_instance_upload(
    true, vertexCount, instanceCount, stride, 1000000u, 1u << 25u, 256u);
constexpr auto chunks = game_sm3_plan_native_instance_chunk(
    vertexCount, instanceCount, stride, 1000000u, 1u << 25u);
static_assert(plan.mode == GameSm3NativeUploadMode::segmented);
static_assert(chunks.instancesPerChunk == 131u);
static_assert(chunks.firstUploadBytes == 33536000u);
static_assert(game_sm3_extended_instance_upload_allowed(
    vertexCount, instanceCount, stride, 128u, 256u, 1ull << 26u));
static_assert(!game_sm3_extended_instance_upload_allowed(
    8000u, instanceCount, stride, 128u, 256u, 1ull << 26u));
static_assert(!game_sm3_extended_instance_upload_allowed(
    vertexCount, 257u, stride, 128u, 256u, 1ull << 26u));
static_assert(game_sm3_extended_instance_upload_allowed(
    8000u, 128u, stride, 128u, 256u, 1ull << 26u)); // old path unchanged
static_assert(!game_sm3_extended_instance_upload_allowed(
    UINT32_MAX, UINT32_MAX, UINT32_MAX, 128u, 256u, UINT64_MAX));
int main() {
    // Exercise the same absolute D3D9 frequency steps as the native live
    // bridge, with a shortened CPU sample independent of the 32 MiB planner.
    constexpr std::uint32_t count = 192u;
    constexpr std::uint32_t vertices = 2u;
    std::array<float, vertices> mesh{{1.0f, 2.0f}};
    std::array<float, count / 3u> sourceInstances{};
    for (std::uint32_t i = 0u; i < sourceInstances.size(); ++i)
        sourceInstances[i] = 1000.0f + static_cast<float>(i);
    std::array<GameSm3StreamView,16> sources{};
    sources[0] = {reinterpret_cast<const std::uint8_t*>(mesh.data()), 4u, vertices};
    sources[1] = {reinterpret_cast<const std::uint8_t*>(sourceInstances.data()),
                  4u, static_cast<std::uint32_t>(sourceInstances.size())};
    const std::vector<GameSm3ElementRef> elements{{0u,0u,0u},{1u,0u,0u}};
    std::array<std::uint32_t,16> steps{};
    steps[1] = 3u;
    std::vector<std::uint8_t> full, segment;
    assert(game_sm3_assemble_instanced_streams(
        elements, sources, vertices, count, steps, full));
    constexpr std::uint32_t countPerUpload = 73u;
    std::uint32_t totalDraws = 0u, uploads = 0u;
    for (std::uint32_t first = 0u; first < count; first += countPerUpload) {
        const auto current = (std::min)(countPerUpload, count-first);
        assert(game_sm3_assemble_instanced_streams(
            elements, sources, vertices, current, steps, segment, first));
        assert(segment.size() == current * vertices * 32u);
        assert(std::memcmp(segment.data(), full.data() + first * vertices * 32u,
                           segment.size()) == 0);
        ++uploads;
        totalDraws += current;
    }
    assert(uploads == 3u && totalDraws == count);
    const auto prior = segment;
    sources[1].vertexCount = 63u; // final source record absent: fail closed
    assert(!game_sm3_assemble_instanced_streams(
        elements, sources, vertices, 1u, steps, segment, 191u));
    assert(segment == prior);
}
