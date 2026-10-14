#include "../src/vr/d3d11/native_game_frame_publication.hpp"
#include "../src/vr/d3d11/native_game_readback_provenance.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
// 10 MHz high-resolution clock gives a 5000-tick / 0.5-ms budget.
constexpr bool full_game_fence_contract() {
    constexpr auto f = GameNativeFramePublication::retry_same_present_fence;
    GameReadbackProvenance same{90u, 3u, 0x4321u, 5u};
    if (!same.may_present(90u, true) || same.may_present(91u, true))
        return false;
    if (!f(true, true, 0u, 0u, 10000000u) ||
        !f(true, true, 10u, 4999u, 10000000u) ||
        f(true, true, 11u, 5000u, 10000000u) ||
        f(true, true, 512u, 0u, 10000000u))
        return false;
    // Bounded retries are prohibited for inset frames, missing current-fence
    // submissions, zero/invalid timers and any fence from an older Present.
    if (f(false, true, 0u, 0u, 10000000u) ||
        f(true, false, 0u, 0u, 10000000u) ||
        f(true, true, 0u, 0u, 0u) ||
        f(true, true, 0u, 0u, 1999u))
        return false;
    return !same.may_present(91u, true) &&
        !GameNativeFramePublication::should_upload(true, false, true, 1u) &&
        !GameNativeFramePublication::should_upload(true, true, false, 1u) &&
        GameNativeFramePublication::should_upload(true, true, true, 0u);
}
static_assert(full_game_fence_contract(), "Bounded same-Present game frame and fallback");
int main() { assert(full_game_fence_contract()); return 0; }
