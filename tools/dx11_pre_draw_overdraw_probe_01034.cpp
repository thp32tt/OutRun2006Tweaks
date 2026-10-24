// Real-game D3D9 ColorFill pre-Draw capture -> native replay acceptance.
// Tests the production mutation/replay headers, not a synthetic WARP shape.
#include "native_game_pre_draw_replay.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
constexpr std::uint32_t W = 40u, H = 16u;
using Frame = std::array<std::uint32_t, W * H>;
void paint(Frame& out, const GameNativePreDrawFills::Fill& f) {
    for (auto y = f.top; y < f.bottom; ++y)
        for (auto x = f.left; x < f.right; ++x)
            out[static_cast<std::size_t>(y) * W + static_cast<std::size_t>(x)] = f.argb;
}
bool append(GameNativePreDrawFills& batch, Frame& reference,
            std::int64_t l, std::int64_t t, std::int64_t r, std::int64_t b,
            std::uint32_t color) {
    GameNativeSourceMutation::ColorFillRect clipped{};
    if (GameNativeSourceMutation::classify_color_fill_rect(
            l,t,r,b,W,H,clipped) != GameNativeSourceMutation::ColorFillClip::Pixels)
        return false;
    if (!batch.record(77u, 88u, l,t,r,b,W,H,color)) return false;
    paint(reference, {clipped.left,clipped.top,clipped.right,clipped.bottom,color});
    return true;
}
Frame replay(const GameNativePreDrawFills& batch) {
    Frame output{};
    std::uint32_t n = 0u;
    const auto consume = [&](const GameNativePreDrawTile& t) {
        const auto byte = [](float value) -> std::uint32_t {
            return static_cast<std::uint32_t>(value * 255.0f + 0.5f);
        };
        const std::uint32_t color =
            (byte(t.rgba[3]) << 24u) | (byte(t.rgba[0]) << 16u) |
            (byte(t.rgba[1]) << 8u) | byte(t.rgba[2]);
        paint(output, {t.left,t.top,t.right,t.bottom,color});
        ++n;
        return true;
    };
    assert(game_native_replay_pre_draw_fills(
        batch,77u,88u,W,H,false,false,consume,consume));
    assert(n == batch.count);
    return output;
}
}
int main() {
    // 16 real distinct D3D9 writes followed by a last rect which supersedes
    // all 16. Previously rejected as capacity overflow despite identical pixels.
    GameNativePreDrawFills batch{};
    Frame expected{};
    for (std::uint32_t i=0; i<16u; ++i) {
        const auto x = static_cast<std::int64_t>(i * 2u);
        assert(append(batch,expected,x,0,x+2,4,0x10102030u+i));
    }
    assert(batch.count == 16u);
    assert(append(batch,expected,0,0,32,4,0x7f8090a0u));
    assert(batch.count == 1u && replay(batch) == expected);
    // Same-color immediately preceding superset must not consume a slot.
    assert(append(batch,expected,2,1,4,2,0x7f8090a0u));
    assert(batch.count == 1u && replay(batch) == expected);

    // Intervening color changes prevent unsafe same-color deduplication.
    batch.discard(); expected = {};
    assert(append(batch,expected,0,0,20,8,0xff123456u));
    assert(append(batch,expected,4,1,12,4,0xffabcdefu));
    assert(append(batch,expected,6,2,8,3,0xff123456u));
    assert(batch.count == 3u && replay(batch) == expected);
    // New rect can replace an earlier enclosed rect while retaining a later
    // partially-overlapping rect in its original source order.
    assert(append(batch,expected,0,0,5,5,0xff555555u));
    assert(batch.count == 4u && replay(batch) == expected);

    // Over capacity with 17 actually distinct writes must fail transactionally.
    batch.discard(); expected = {};
    for (std::uint32_t i=0; i<16u; ++i)
        assert(append(batch,expected,i*2u,0,i*2u+1u,1,0xff000000u+i));
    const auto before = batch.entries;
    assert(!batch.record(77u,88u,34,0,35,1,W,H,0xffabcdefu));
    assert(batch.count == 16u);
    for (std::size_t i=0; i<before.size(); ++i) {
        assert(batch.entries[i].left==before[i].left);
        assert(batch.entries[i].right==before[i].right);
        assert(batch.entries[i].argb==before[i].argb);
    }
    assert(replay(batch) == expected);
    assert(!batch.record(79u,88u,0,0,40,16,W,H,0xffffffffu));
    assert(batch.count == 16u && replay(batch) == expected);
    assert(!batch.record(77u,88u,7,1,7,2,W,H,0xffffffffu));
    assert(batch.count == 16u);
    // No-op clipped offscreen write is allowed and consumes no tile.
    assert(batch.record(77u,88u,41,0,45,2,W,H,0xffffffffu));
    assert(batch.count == 16u);
    assert(!game_native_replay_pre_draw_fills(
        batch,77u,89u,W,H,false,false,
        [](const GameNativePreDrawTile&) { return true; },
        [](const GameNativePreDrawTile&) { return true; }));
}
