#include "live_game_sm3_connected_instances.hpp"
#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    const float vertices[]{1.f,2.f,3.f,4.f};
    const float instances[]{10.f,20.f};
    std::array<GameSm3StreamView,16> streams{};
    streams[0]={reinterpret_cast<const std::uint8_t*>(vertices),4u,4u};
    streams[15]={reinterpret_cast<const std::uint8_t*>(instances),4u,2u};
    std::vector<GameSm3ElementRef> elements{{0u,0u,0u},{15u,0u,0u}};
    std::array<std::uint32_t,16> step{}; step[15]=1u;
    std::vector<std::uint8_t> geometry;
    assert(game_sm3_assemble_instanced_streams(elements, streams, 4u, 2u, step, geometry));
    assert(geometry.size()==256u);
    float lastValue=0.f;
    std::memcpy(&lastValue, geometry.data()+7u*32u+16u,4u);
    assert(lastValue==20.f);
    std::vector<std::uint32_t> indices;
    assert(game_sm3_expand_connected_instance_indices(3u,nullptr,4u,4u,2u,1024u,indices));
    assert((indices==std::vector<std::uint32_t>{0,1,1,2,2,3,4,5,5,6,6,7}));
    const std::uint32_t reverse[]{3,2,1,0};
    assert(game_sm3_expand_connected_instance_indices(5u,reverse,4u,4u,2u,1024u,indices));
    assert((indices==std::vector<std::uint32_t>{3,2,1,1,2,0,7,6,5,5,6,4}));
    assert(game_sm3_expand_connected_instance_indices(6u,nullptr,4u,4u,2u,1024u,indices));
    assert((indices==std::vector<std::uint32_t>{0,1,2,0,2,3,4,5,6,4,6,7}));
    const auto good=indices;
    const std::uint32_t invalid[]{0,1,2,4};
    assert(!game_sm3_expand_connected_instance_indices(5u,invalid,4u,4u,2u,1024u,indices));
    assert(!game_sm3_expand_connected_instance_indices(3u,nullptr,4u,4u,2u,10u,indices));
    assert(!game_sm3_expand_connected_instance_indices(6u,nullptr,2u,4u,2u,1024u,indices));
    assert(!game_sm3_expand_connected_instance_indices(4u,nullptr,4u,4u,2u,1024u,indices));
    // One physical instance is legal for the last WRITE_DISCARD GPU chunk
    // of a segmented authentic source strip/fan. It must preserve winding
    // and use indices local to that chunk, without splicing its predecessor.
    assert(indices==good); // Earlier rejected inputs preserve the destination.
    assert(game_sm3_expand_connected_instance_indices(
        5u,nullptr,4u,4u,1u,1024u,indices));
    assert((indices==std::vector<std::uint32_t>{0,1,2,2,1,3}));
    const auto oneInstance=indices;
    assert(!game_sm3_expand_connected_instance_indices(
        5u,nullptr,4u,4u,0u,1024u,indices));
    assert(!game_sm3_expand_connected_instance_indices(3u,nullptr,3u,4u,
        (std::numeric_limits<std::uint32_t>::max)(),1024u,indices));
    assert(indices==oneInstance);
}
