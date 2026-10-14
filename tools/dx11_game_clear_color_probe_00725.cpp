#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
#include <array>
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool test_clear() {
    GameNativeClearColor game{};
    constexpr std::array<float, 4> fallback{0.035f, 0.035f, 0.08f, 1.0f};
    if (game.native_color(0x10u, 0x20u, fallback) != fallback) return false;
    game.record(0x10u, 0x20u, 0xff0000ffu, true); // opaque blue menu Clear
    const auto blue = game.native_color(0x10u, 0x20u, fallback);
    if (blue[0] != 0.0f || blue[1] != 0.0f || blue[2] != 1.0f || blue[3] != 1.0f)
        return false;
    if (game.native_color(0x11u, 0x20u, fallback) != fallback ||
        game.native_color(0x10u, 0x21u, fallback) != fallback) return false;
    game.record(0x10u, 0x20u, 0x00ff0000u, false); // partial race scene
    if (game.native_color(0x10u, 0x20u, fallback) != fallback) return false;
    game.record(0x10u, 0x20u, 0xffff0000u, true); // red vehicle menu
    if (game.native_color(0x10u, 0x20u, fallback)[0] != 1.0f) return false;
    GameNativeFrameBatch frame{};
    frame.succeeded(false);
    frame.scene_boundary(); // later Clear aborts already-submitted native Draw
    if (frame.publishable(true)) return false;
    game.discard();
    return game.native_color(0x10u, 0x20u, fallback) == fallback;
}
static_assert(test_clear(), "real game Clear -> native color + fallback");
int main() { assert(test_clear()); return 0; }
