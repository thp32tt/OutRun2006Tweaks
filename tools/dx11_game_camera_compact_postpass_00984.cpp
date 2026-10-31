#include "../src/vr/d3d11/native_game_offscreen_color_provenance.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11;
using Region = NativeGameOffscreenColorRegion;
using Key = NativeGameOffscreenColorKey;
struct Slot { Key key{}; Region region{}; };
template <std::size_t N>
bool insert(std::array<Slot,N>& ledger, Key key, Region region) {
    if (!native_game_offscreen_color_region_valid(region) || !key.resource) return false;
    bool joined = true;
    while (joined) {
        joined = false;
        for (auto& entry : ledger) {
            if (!native_game_offscreen_color_key_matches(key,entry.key)) continue;
            Region exact{};
            if (!native_game_offscreen_exact_rect_union(region,entry.region,exact)) continue;
            region = exact;
            entry = {};
            joined = true;
        }
    }
    for (auto& entry : ledger) {
        if (!entry.key.resource) { entry={key,region}; return true; }
    }
    return false;
}
int main() {
    constexpr Key camera{0x1200u,0u,0u};
    constexpr Key foreignMip{0x1200u,0u,1u};
    constexpr Key otherEye{0x1200u,1u,0u};
    std::array<Slot,32> ledger{};
    // The 64 genuine sequential GPU camera strips must not lose provenance
    // after 32 entries; they form one contiguous source for a Copy/Stretch.
    for (std::uint32_t x=0; x<64; ++x)
        assert(insert(ledger,camera,{x,0u,x+1u,72u}));
    assert(ledger[0].region.left==0u && ledger[0].region.right==64u);
    assert(insert(ledger,camera,{0u,72u,64u,96u}));
    assert(ledger[0].region.bottom==96u);
    std::array<Region,32> written{};
    std::size_t count=0;
    for (const auto& s:ledger) if (native_game_offscreen_color_key_matches(
        camera,s.key)) written[count++]=s.region;
    assert(native_game_offscreen_color_region_fully_covered(
        {0u,0u,64u,96u},written,count));
    // Different mip or stereo array slice cannot authenticate camera 0.
    assert(insert(ledger,foreignMip,{64u,0u,96u,96u}));
    assert(insert(ledger,otherEye,{64u,0u,96u,96u}));
    assert(ledger[0].region.right==64u);
    // A physical missing texel or L-shaped union must remain unproven.
    Region joined{};
    assert(!native_game_offscreen_exact_rect_union(
        {0u,0u,16u,20u},{17u,0u,32u,20u},joined));
    assert(!native_game_offscreen_exact_rect_union(
        {0u,0u,16u,20u},{16u,10u,32u,30u},joined));
    assert(!native_game_offscreen_exact_rect_union(
        {0u,0u,16u,20u},{16u,20u,32u,40u},joined));
    assert(native_game_offscreen_exact_rect_union(
        {0u,0u,16u,20u},{4u,4u,10u,10u},joined));
    assert(joined.left==0u && joined.right==16u && joined.bottom==20u);
    std::array<Slot,32> disjoint{};
    for(std::uint32_t x=0;x<32u;++x)
        assert(insert(disjoint,camera,{x*3u,0u,x*3u+1u,20u}));
    // Saturated by separated genuine commands: fail closed, not coverage.
    assert(!insert(disjoint,camera,{100u,0u,101u,20u}));
    assert(!native_game_offscreen_color_region_fully_covered(
        {0u,0u,96u,20u},written,0u));
}
