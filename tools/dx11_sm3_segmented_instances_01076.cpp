#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
static float at(const std::vector<std::uint8_t>& bytes, std::size_t n) {
    float f{};
    std::memcpy(&f, bytes.data() + n * sizeof(float), sizeof(float));
    return f;
}
int main() {
    // Genuine two-stream D3D9 INDEXEDDATA + INSTANCEDATA: two per-vertex
    // coordinates, one instance color advancing only every two instances.
    const float vertices[2] = {11.0f, 22.0f};
    const float records[4] = {101.0f, 202.0f, 303.0f, 404.0f};
    std::vector<GameSm3ElementRef> decl{{0,0,0},{1,0,0}};
    std::array<GameSm3StreamView,16> streams{};
    streams[0] = {reinterpret_cast<const std::uint8_t*>(vertices),4,2};
    streams[1] = {reinterpret_cast<const std::uint8_t*>(records),4,4};
    std::array<std::uint32_t,16> steps{};
    steps[1] = 2u;
    std::vector<std::uint8_t> full;
    assert(game_sm3_assemble_instanced_streams(
        decl,streams,2u,6u,steps,full));
    assert(full.size() == 6u*2u*32u);
    std::vector<std::uint8_t> segment;
    for (std::uint32_t instance=0;instance<6u;++instance) {
        assert(game_sm3_assemble_instanced_streams(
            decl,streams,2u,1u,steps,segment,instance));
        assert(segment.size() == 64u);
        assert(std::memcmp(segment.data(),full.data()+instance*64u,64u)==0);
        assert(at(segment,0u)==11.0f);
        assert(at(segment,8u)==22.0f);
        assert(at(segment,4u)==records[instance/2u]);
        assert(at(segment,12u)==records[instance/2u]);
    }
    // Missing later instance record rejects BEFORE output swap: never
    // mistake record zero for global instance five after a new GPU upload.
    const auto preserved=segment;
    streams[1].vertexCount=2u;
    assert(!game_sm3_assemble_instanced_streams(
        decl,streams,2u,1u,steps,segment,5u));
    assert(segment==preserved);
    // Explicitly reject overflowing original ordinal and unknown source
    // stride instead of reading beyond the captured D3D9 CPU shadow.
    streams[1].vertexCount=4u;
    assert(!game_sm3_assemble_instanced_streams(
        decl,streams,2u,2u,steps,segment,UINT32_MAX));
    assert(segment==preserved);
    streams[0].stride=0u;
    assert(!game_sm3_assemble_instanced_streams(
        decl,streams,2u,1u,steps,segment,0u));
    assert(segment==preserved);
}
