#include "../src/vr/d3d11/native_game_live_shader_cache.hpp"
#include <cassert>
#include <cstdint>
#include <unordered_map>
using outrun::vr::dx11::live_game_frame::LiveGameShaderCacheReplacement;
struct Resident { std::uint64_t lastUse{}; int payload{}; };
int main() {
    std::unordered_map<unsigned, Resident> programs;
    for (unsigned i = 0; i < 64; ++i)
        programs.emplace(i, Resident{i + 1u, static_cast<int>(i)});
    // The 65th real game pair is no longer denied merely for cache pressure.
    assert(LiveGameShaderCacheReplacement::retire_oldest_if_full(programs, 64u));
    assert(programs.size() == 63u && !programs.count(0u));
    programs.emplace(100u, Resident{65u, 100});
    // Recently used menu shaders survive a later vehicle/race transition.
    programs.at(1u).lastUse = 1000u;
    assert(LiveGameShaderCacheReplacement::retire_oldest_if_full(programs, 64u));
    assert(!programs.count(2u) && programs.count(1u) && programs.count(100u));
    programs.emplace(200u, Resident{1001u, 200});
    // Blend and shader cache families share the same replacement rule.
    std::unordered_map<unsigned, Resident> blends{{1u, {2u, 42}},
                                                   {2u, {1u, 11}}};
    assert(LiveGameShaderCacheReplacement::retire_oldest_if_full(blends, 2u));
    assert(!blends.count(2u) && blends.count(1u));
    assert(!LiveGameShaderCacheReplacement::retire_oldest_if_full(blends, 0u));
    assert(blends.size() == 1u);
    // A non-full cache never discards working objects before creation.
    assert(LiveGameShaderCacheReplacement::retire_oldest_if_full(blends, 2u));
    assert(blends.size() == 1u);
}
