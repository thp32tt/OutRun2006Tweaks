#include "live_game_sm3_instance_batches.hpp"
#include "live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
static float channel(const std::vector<std::uint8_t>& v,unsigned n,unsigned k) {
    float result=0.f; std::memcpy(&result,v.data()+n*32u+k*16u,4u);
    return result;
}
int main() {
    static_assert(game_sm3_independent_list(1u) &&
                  game_sm3_independent_list(2u) &&
                  game_sm3_independent_list(4u) &&
                  !game_sm3_independent_list(3u) &&
                  !game_sm3_independent_list(5u) &&
                  !game_sm3_independent_list(6u));
    const float vertices[]{1.f,2.f,3.f}, instances[]{10.f,20.f};
    std::array<GameSm3StreamView,16> streams{};
    streams[0]={reinterpret_cast<const std::uint8_t*>(vertices),4u,3u};
    streams[15]={reinterpret_cast<const std::uint8_t*>(instances),4u,2u};
    const std::vector<GameSm3ElementRef> elements{{0u,0u,0u},{15u,0u,0u}};
    std::array<std::uint32_t,16> steps{}; steps[15]=1u;
    std::vector<std::uint8_t> expanded;
    assert(game_sm3_assemble_instanced_streams(elements,streams,3u,2u,steps,expanded));
    assert(expanded.size()==192u);
    assert(channel(expanded,0u,0u)==1.f && channel(expanded,5u,0u)==3.f);
    assert(channel(expanded,0u,1u)==10.f && channel(expanded,4u,1u)==20.f);
    const std::uint32_t original[]{2u,0u,1u},invalid[]{3u,0u,1u};
    std::vector<std::uint32_t> indices;
    assert(game_sm3_expand_list_instance_indices(original,3u,3u,2u,indices));
    assert((indices==std::vector<std::uint32_t>{2,0,1,5,3,4}));
    const auto good=indices;
    assert(!game_sm3_expand_list_instance_indices(invalid,3u,3u,2u,indices));
    assert(!game_sm3_expand_list_instance_indices(nullptr,3u,3u,2u,indices));
    assert(!game_sm3_expand_list_instance_indices(original,3u,3u,1u,indices));
    assert(!game_sm3_expand_list_instance_indices(original,3u,3u,
        (std::numeric_limits<std::uint32_t>::max)(),indices));
    assert(indices==good);
}
