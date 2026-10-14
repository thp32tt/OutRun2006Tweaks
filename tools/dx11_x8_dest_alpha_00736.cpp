#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool proof() {
    constexpr std::uintptr_t device = 0x100u, target = 0x200u;
    constexpr std::array<float, 4> fallback{0.03f, 0.04f, 0.05f, 1.0f};
    GameNativeClearColor clear{};
    GameNativeFrameBatch frame{};
    if (clear.native_color(device, target, fallback) != fallback) return false;
    clear.record(device, target, 0x00112233u, true, false); // A8, zero alpha
    if (clear.native_color(device, target, fallback)[3] != 0.0f) return false;
    clear.record(device, target, 0x00112233u, true, true);  // X8, reserved alpha=0
    auto x8 = clear.native_color(device, target, fallback);
    if (x8[3] != 1.0f || x8[0] != float(0x11u)/255.0f ||
        x8[1] != float(0x22u)/255.0f || x8[2] != float(0x33u)/255.0f) return false;
    if (!frame.accepts_full_seeded(0u, clear.matches(device, target))) return false;
    frame.succeeded(false); frame.record_source_draw(0u);
    if (!frame.accepts_full_seeded(1u, false)) return false; // next indexed Draw
    if (clear.native_color(device, target + 1u, fallback) != fallback ||
        clear.native_color(device + 1u, target, fallback) != fallback) return false;
    clear.record(device, target, 0x80112233u, true, false); // A8 retained
    if (clear.native_color(device, target, fallback)[3] != 128.0f/255.0f) return false;
    clear.record(device, target, 0x00112233u, false, true); // partial Clear rejects seed
    if (clear.opaqueDestinationAlpha || clear.matches(device, target)) return false;
    if (clear.native_color(device, target, fallback) != fallback) return false;
    clear.record(device, target, 0x00112233u, true, true);
    clear.discard(); // Reset/Present flushes stale source format
    return !clear.opaqueDestinationAlpha && !clear.matches(device, target);
}
static_assert(proof(), "DX9 X8 destination alpha must be opaque in native full frame");
int main() { assert(proof()); return 0; }
