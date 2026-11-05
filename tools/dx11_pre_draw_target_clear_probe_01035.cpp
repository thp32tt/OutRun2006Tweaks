// Actual D3D9 TARGET-only pre-Draw Clear -> ordered D3D11 ClearView/raster
// replay, sharing the real ColorFill recorder and rejecting partial commits.
#include "native_game_pre_draw_replay.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstddef>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct D3DRect { int x1, y1, x2, y2; };
constexpr std::uint32_t W=40u, H=18u;
using Frame=std::array<std::uint32_t, W*H>;
void paint(Frame& frame, std::int64_t l, std::int64_t t,
           std::int64_t r, std::int64_t b, std::uint32_t color) {
    for (auto y=t; y<b; ++y)
        for (auto x=l; x<r; ++x)
            frame[static_cast<std::size_t>(y)*W+static_cast<std::size_t>(x)]=color;
}
std::uint32_t unpack(float red, float green, float blue, float alpha) {
    const auto b=[](float v){return static_cast<std::uint32_t>(v*255.0f+0.5f);};
    return (b(alpha)<<24u)|(b(red)<<16u)|(b(green)<<8u)|b(blue);
}
Frame replay(const GameNativePreDrawFills& entries) {
    Frame output{};
    const auto gpu=[&](const GameNativePreDrawTile& tile) noexcept {
        paint(output,tile.left,tile.top,tile.right,tile.bottom,
              unpack(tile.rgba[0],tile.rgba[1],tile.rgba[2],tile.rgba[3]));
        return true;
    };
    assert(game_native_replay_pre_draw_fills(
        entries,17u,19u,W,H,false,false,gpu,gpu));
    return output;
}
}
int main() {
    GameNativePreDrawFills pending{};
    Frame expected{};
    assert(pending.record(17u,19u,0,0,12,10,W,H,0xff223344u));
    paint(expected,0,0,12,10,0xff223344u);
    // Two source D3DRECTs clipped to viewport x=4..24, y=2..14.
    const D3DRect partial[]={{-20,-10,9,6},{14,8,29,17}};
    assert(pending.record_target_clear(
        17u,19u,W,H,4,2,20,12,2,partial,0xffaabbccu));
    paint(expected,4,2,9,6,0xffaabbccu);
    paint(expected,14,8,24,14,0xffaabbccu);
    assert(pending.record(17u,19u,6,3,19,9,W,H,0xff556677u));
    paint(expected,6,3,19,9,0xff556677u);
    assert(replay(pending)==expected);
    // Count=0 means clear the viewport, not the entire backbuffer.
    assert(pending.record_target_clear(
        17u,19u,W,H,2,0,30,16,0,static_cast<const D3DRect*>(nullptr),
        0xff123456u));
    paint(expected,2,0,32,16,0xff123456u);
    assert(replay(pending)==expected);
    // The 24 authentic source writes reduce to one ordered opaque tile.
    // A count above the storage limit must not discard a valid game Clear.
    std::array<D3DRect,24> nested{};
    for (std::size_t i=0;i<nested.size();++i)
        nested[i]={0,0,static_cast<int>(i%12u+1u),5};
    assert(pending.record_target_clear(
        17u,19u,W,H,0,0,W,H,
        static_cast<std::uint32_t>(nested.size()),nested.data(),0xffdead11u));
    paint(expected,0,0,12,5,0xffdead11u);
    assert(replay(pending)==expected);
    const auto prior=pending;
    const D3DRect bad[]={{1,2,4,8},{7,10,3,12}};
    assert(!pending.record_target_clear(
        17u,19u,W,H,0,0,W,H,2,bad,0xffeeeeeeu));
    assert(pending.count==prior.count && replay(pending)==replay(prior));
    assert(!pending.record_target_clear(
        17u,20u,W,H,0,0,W,H,2,partial,0xff010203u));
    assert(!pending.record_target_clear(
        17u,19u,W,H,0,0,W,H,129u,partial,0xff010203u));
    assert(pending.count==prior.count && replay(pending)==replay(prior));
    // Entirely disjoint successful D3D9 Clear writes zero pixels.
    const D3DRect outside[]={{100,100,120,120}};
    assert(pending.record_target_clear(
        17u,19u,W,H,0,0,W,H,1,outside,0xffaabbccu));
    assert(replay(pending)==expected);
    // 128 independent authentic color regions are now staged intact for
    // D3D11 first-Draw RTV replay; the 129th fails without partial writes.
    pending.discard(); expected={};
    for(int i=0;i<128;++i) {
        const int x=(i%20)*2,y=(i/20)*2;
        const auto argb=0xff000000u+static_cast<std::uint32_t>(i);
        assert(pending.record(17u,19u,x,y,x+1,y+1,W,H,argb));
        paint(expected,x,y,x+1,y+1,argb);
    }
    const auto saved=pending;
    const D3DRect overflow[]={{0,16,1,17}};
    assert(!pending.record_target_clear(
        17u,19u,W,H,0,0,W,H,1,overflow,0xffabcdefu));
    assert(pending.count==128u && replay(pending)==replay(saved));
    assert(replay(pending)==expected);
    // The per-original-call source guard also rejects malformed 129 input
    // without any attempt at native GPU pixels.
    assert(!pending.record_target_clear(
        17u,19u,W,H,0,0,W,H,129u,overflow,0xffabcdefu));
    assert(replay(pending)==expected);
}
