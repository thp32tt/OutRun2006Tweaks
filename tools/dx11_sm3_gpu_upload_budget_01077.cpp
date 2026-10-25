#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
constexpr auto bytesOnly = game_sm3_plan_native_instance_upload(
    true, 65536u, 2u, 384u, 100000u, 1u << 25u, 128u);
static_assert(bytesOnly.mode == GameSm3NativeUploadMode::segmented);
static_assert(bytesOnly.vertexBytes == 65536u * 384u);
// D3D9 float3 stride 12 is promoted to native FLOAT4 stride 16 for source
// instancing. Using 12 would incorrectly choose a flat GPU upload.
constexpr auto rawStrideDecision = game_sm3_plan_native_instance_upload(
    true, 500u, 2u, 12u, 10000u, 13000u, 128u);
constexpr auto nativeStrideDecision = game_sm3_plan_native_instance_upload(
    true, 500u, 2u, 16u, 10000u, 13000u, 128u);
static_assert(rawStrideDecision.mode == GameSm3NativeUploadMode::flat);
static_assert(nativeStrideDecision.mode == GameSm3NativeUploadMode::segmented);
static_assert(nativeStrideDecision.vertexBytes == 8000u);
constexpr auto countOnly = game_sm3_plan_native_instance_upload(
    true, 60000u, 2u, 32u, 100000u, 1u << 25u, 128u);
static_assert(countOnly.mode == GameSm3NativeUploadMode::segmented);
constexpr auto fitting = game_sm3_plan_native_instance_upload(
    true, 1000u, 3u, 32u, 100000u, 1u << 25u, 128u);
static_assert(fitting.mode == GameSm3NativeUploadMode::flat);
static_assert(fitting.vertexBytes == 96000u);
static_assert(game_sm3_plan_native_instance_upload(
    true, 65536u, 129u, 384u, 100000u, 1u << 25u, 128u
    ).mode == GameSm3NativeUploadMode::invalid);
static_assert(game_sm3_plan_native_instance_upload(
    true, 65536u, 2u, 513u, 100000u, 1u << 25u, 128u
    ).mode == GameSm3NativeUploadMode::invalid);
static_assert(game_sm3_plan_native_instance_upload(
    false, 65536u, 2u, 384u, 100000u, 1u << 25u, 128u
    ).mode == GameSm3NativeUploadMode::invalid);
static_assert(game_sm3_plan_native_instance_upload(
    true, 65536u, 2u, 384u, 10000u, 1u << 25u, 128u
    ).mode == GameSm3NativeUploadMode::invalid);
static_assert(game_sm3_plan_native_instance_upload(
    true, 65536u, 1u, 512u, 100000u, 1u << 25u, 128u
    ).mode == GameSm3NativeUploadMode::flat);
int main() {
    // Byte budget selects segments; actual D3D9 vertex/instance stream
    // assembly remains sourced at the global instance ordinal.
    const float sourceVertices[] = {9.0f, 19.0f};
    const float instanceRecords[] = {101.0f, 202.0f, 303.0f};
    std::array<GameSm3StreamView,16> streams{};
    streams[0] = {reinterpret_cast<const std::uint8_t*>(sourceVertices),4u,2u};
    streams[1] = {reinterpret_cast<const std::uint8_t*>(instanceRecords),4u,3u};
    std::vector<GameSm3ElementRef> elements{{0u,0u,0u},{1u,0u,0u}};
    std::array<std::uint32_t,16> steps{};
    steps[1] = 2u;
    const auto byteLimit = game_sm3_plan_native_instance_upload(
        true, 2u, 5u, 32u, 100u, 64u, 128u);
    assert(byteLimit.mode == GameSm3NativeUploadMode::segmented);
    assert(byteLimit.vertexBytes == 64u);
    std::vector<std::uint8_t> output;
    for (std::uint32_t instance = 0u; instance < 5u; ++instance) {
        assert(game_sm3_assemble_instanced_streams(
            elements, streams, 2u, 1u, steps, output, instance));
        assert(output.size() == byteLimit.vertexBytes);
        float vertex{}, record{};
        std::memcpy(&vertex,output.data(),4u);
        std::memcpy(&record,output.data()+16u,4u);
        assert(vertex == 9.0f && record == instanceRecords[instance / 2u]);
    }
    const auto saved = output;
    streams[1].vertexCount = 2u;
    assert(!game_sm3_assemble_instanced_streams(
        elements,streams,2u,1u,steps,output,4u));
    assert(output == saved); // fail closed, no partially committed segment
}
