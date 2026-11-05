#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <array>
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool equal_color(const std::array<float, 4>& lhs,
                           const std::array<float, 4>& rhs) noexcept {
    for (std::size_t i = 0; i < lhs.size(); ++i)
        if (lhs[i] != rhs[i]) return false;
    return true;
}
constexpr bool proof() {
    constexpr std::uintptr_t device = 0x100u, target = 0x200u;
    constexpr std::array<float, 4> fallback{0.03f, 0.04f, 0.05f, 1.0f};
    GameNativeClearColor clear{};
    GameNativeFrameBatch frame{};
    if (!equal_color(clear.native_color(device, target, fallback), fallback)) return false;
    clear.record(device, target, 0x00112233u, true, false); // A8, zero alpha
    if (clear.native_color(device, target, fallback)[3] != 0.0f) return false;
    clear.record(device, target, 0x00112233u, true, true);  // X8, reserved alpha=0
    auto x8 = clear.native_color(device, target, fallback);
    if (x8[3] != 1.0f || x8[0] != float(0x11u)/255.0f ||
        x8[1] != float(0x22u)*(1.0f/255.0f) ||
        x8[2] != float(0x33u)*(1.0f/255.0f)) return false;
    // RGB writes stay enabled; X8 cannot mutate alpha after native Draw.
    if (clear.native_write_mask(device, target, 0x0fu) != 0x07u ||
        clear.native_write_mask(device, target, 0x08u) != 0u ||
        clear.native_write_mask(device, target, 0x05u) != 0x05u ||
        clear.native_write_mask(device + 1u, target, 0x0fu) != 0x0fu ||
        clear.native_write_mask(device, target + 1u, 0x0fu) != 0x0fu)
        return false;
    if (!frame.accepts_full_seeded(0u, clear.matches(device, target))) return false;
    frame.succeeded(false); frame.record_source_draw(0u);
    if (!frame.accepts_full_seeded(1u, false)) return false; // next indexed Draw
    if (!equal_color(clear.native_color(device, target + 1u, fallback), fallback) ||
        !equal_color(clear.native_color(device + 1u, target, fallback), fallback)) return false;
    clear.record(device, target, 0x80112233u, true, false); // A8 retained
    if (clear.native_color(device, target, fallback)[3] != 128.0f/255.0f ||
        clear.native_write_mask(device, target, 0x0fu) != 0x0fu) return false;
    clear.record(device, target, 0x00112233u, false, true); // partial Clear rejects seed
    if (clear.opaqueDestinationAlpha || clear.matches(device, target) ||
        clear.native_write_mask(device, target, 0x0fu) != 0x0fu) return false;
    if (!equal_color(clear.native_color(device, target, fallback), fallback)) return false;
    clear.record(device, target, 0x00112233u, true, true);
    clear.discard(); // Reset/Present flushes stale source format
    return !clear.opaqueDestinationAlpha && !clear.matches(device, target);
}
static_assert(proof(), "DX9 X8 destination alpha must be opaque in native full frame");
int main() { assert(proof()); return 0; }
