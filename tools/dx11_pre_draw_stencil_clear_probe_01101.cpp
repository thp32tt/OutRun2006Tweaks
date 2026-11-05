// 01101 live D3D9 clipped TARGET|STENCIL and TARGET|Z|STENCIL.
// Native admitted Draws are stencil-disabled; validate main-owner/epoch
// admission and genuine color/depth pixel transactions without inventing
// a native stencil attachment. Original D3D9 Draw remains authoritative.
#include "../src/vr/d3d11/native_game_main_stencil_clear.hpp"
#include "../src/vr/d3d11/native_game_pre_draw_combined_clear.hpp"
#include "../src/vr/d3d11/native_game_pre_draw_replay.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1,y1,x2,y2; };
constexpr std::uint32_t W=32,H=16;
using Pixels=std::array<std::uint32_t,W*H>;
std::uint32_t rgba(const GameNativePreDrawTile& t) {
    auto b=[](float v){ return std::uint32_t(v*255.f+.5f); };
    return (b(t.rgba[3])<<24)|(b(t.rgba[0])<<16)|
           (b(t.rgba[1])<<8)|b(t.rgba[2]);
}
}
int main() {
    static_assert(GameNativeMainStencilClear::may_ignore_pre_draw(
        true,true,true,true,true));
    static_assert(!GameNativeMainStencilClear::may_ignore_pre_draw(
        true,true,false,true,true));
    static_assert(!GameNativeMainStencilClear::may_ignore_pre_draw(
        true,true,true,false,true));
    static_assert(!GameNativeMainStencilClear::may_ignore_pre_draw(
        true,true,true,true,false));
    static_assert(!GameNativeMainStencilClear::may_ignore_pre_draw(
        false,true,true,true,true));
    static_assert(!GameNativeMainStencilClear::may_ignore_pre_draw(
        true,false,true,true,true));
    GameNativePreDrawFills colors{};
    GameNativePreDrawDepth depths{};
    constexpr std::uintptr_t device=7,rt=11,zs=13;
    // An authentic main color seed followed by TARGET|STENCIL changes color
    // but cannot change the D3D11 depth buffer in a stencil-disabled Draw.
    const Rect colorOnly[]={{2,1,10,5}};
    assert(colors.record_target_clear(device,rt,W,H,0,0,W,H,
                                    1,colorOnly,0xff112233u));
    assert(colors.count==1u && depths.count==0u);
    // A later clipped TARGET|Z|STENCIL changes BOTH GPU attachments.
    // Clipping and ordered writes must reproduce the source D3D9 pixels.
    const Rect both[]={{6,3,16,9},{24,8,40,20}};
    assert(GameNativePreDrawCombinedClear::record(
        colors,depths,device,rt,zs,W,H,0,0,W,H,
        2,both,0xffaabbccu,0.25f));
    assert(colors.count==3u && depths.count==2u);
    assert(colors.replay_ready(device,rt,W,H));
    assert(depths.replay_ready(device,rt,zs,W,H));
    Pixels pixels{};pixels.fill(0xff000000u);
    auto replay=[&](const GameNativePreDrawTile& t) noexcept {
        for(auto y=t.top;y<t.bottom;++y)
            for(auto x=t.left;x<t.right;++x)
                pixels[std::size_t(y)*W+std::size_t(x)]=rgba(t);
        return true;
    };
    assert(game_native_replay_pre_draw_fills(
        colors,device,rt,W,H,false,true,replay,replay));
    assert(pixels[2u*W+3u]==0xff112233u);
    assert(pixels[4u*W+7u]==0xffaabbccu);
    assert(pixels[10u*W+27u]==0xffaabbccu);
    assert(pixels[0]==0xff000000u);
    assert(depths.tiles[0].z==0.25f && depths.tiles[1].z==0.25f);
    // Invalid geometry, wrong canonical Z owner and exhausted capacity
    // never partially commit color when depth staging is unavailable.
    const auto c=colors.count,d=depths.count;
    const Rect inverted[]={{9,4,1,7}};
    assert(!GameNativePreDrawCombinedClear::record(
        colors,depths,device,rt,zs,W,H,0,0,W,H,
        1,inverted,0xffaabbccu,.5f));
    assert(!GameNativePreDrawCombinedClear::record(
        colors,depths,device,rt,zs+1,W,H,0,0,W,H,
        2,both,0xffaabbccu,.5f));
    assert(c==colors.count && d==depths.count);
    assert(depths.replay_ready(device,rt,zs,W,H));
}
