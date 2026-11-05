#include "../src/vr/d3d11/native_game_offscreen_color_provenance.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11;
using Region = NativeGameOffscreenColorRegion;
int main() {
    // A non-slicing five-panel source mosaic; no pairwise center merge works.
    constexpr std::array<Region,4> tiles{{
        {0u,0u,4u,2u}, {4u,0u,6u,4u},
        {2u,4u,6u,6u}, {0u,2u,2u,6u}}};
    constexpr Region center{2u,2u,4u,4u};
    for (auto r: tiles) {
        Region pair{};
        assert(!native_game_offscreen_exact_rect_union(center,r,pair));
    }
    const auto covered = native_game_offscreen_color_mosaic_compaction(
        center,tiles,tiles.size());
    assert(covered.left==0u && covered.top==0u &&
           covered.right==6u && covered.bottom==6u);
    // One physically missing camera row must not become color evidence.
    constexpr std::array<Region,4> gap{{
        {0u,0u,4u,2u}, {4u,0u,6u,4u},
        {2u,4u,6u,6u}, {0u,2u,2u,5u}}};
    const auto rejected = native_game_offscreen_color_mosaic_compaction(
        center,gap,gap.size());
    assert(rejected.left==center.left && rejected.top==center.top &&
           rejected.right==center.right && rejected.bottom==center.bottom);
    // A single neighboring strip does not justify a larger source.
    constexpr std::array<Region,1> narrow{{{4u,2u,5u,3u}}};
    assert(native_game_offscreen_color_mosaic_compaction(
        center,narrow,1u).right==4u);
    constexpr NativeGameOffscreenColorKey cam{0xCAFEu,0u,0u};
    constexpr NativeGameOffscreenColorKey otherEye{0xCAFEu,1u,0u};
    constexpr NativeGameOffscreenColorKey otherMip{0xCAFEu,0u,1u};
    std::array<NativeGameOffscreenColorKey,32u> keys{};
    std::array<Region,32u> writes{};
    for (std::size_t i=0;i<4;++i) { keys[i]=cam; writes[i]=tiles[i]; }
    for (std::size_t i=4;i<32;++i) {
        keys[i] = i%2 ? otherEye : otherMip;
        writes[i]={100u,0u,110u,10u};
    }
    std::array<Region,32u> same{};
    std::size_t count=0u;
    for (std::size_t i=0;i<32;++i)
        if (native_game_offscreen_color_key_matches(cam,keys[i]))
            same[count++]=writes[i];
    const auto recovered = native_game_offscreen_color_mosaic_compaction(
        center,same,count);
    assert(recovered.left==0u && recovered.right==6u);
    assert(!native_game_offscreen_color_key_matches(cam,otherEye));
    assert(!native_game_offscreen_color_key_matches(cam,otherMip));
}
