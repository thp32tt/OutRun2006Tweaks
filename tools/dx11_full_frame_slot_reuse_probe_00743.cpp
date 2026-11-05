#include "../src/vr/d3d11/native_game_frame_publication.hpp"
#include "../src/vr/d3d11/native_game_readback_provenance.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;

constexpr bool native_full_frame_slot_reuse() {
    constexpr auto choose = GameNativeFramePublication::select_available_slot;
    // Full-resolution game frame can use any free staging resource even if
    // the preferred slot still holds a not-yet-fenced older frame.
    if (choose(0u, 3u, 0u) != 0u ||
        choose(1u, 3u, 0u) != 1u ||
        choose(3u, 3u, 0u) != 2u ||
        choose(5u, 3u, 0u) != 1u ||
        choose(6u, 3u, 2u) != 0u ||
        choose(2u, 3u, 1u) != 2u)
        return false;
    // All busy/invalid ring config must drop only native diagnostics,
    // never wait for a fence or publish a frame from another Present.
    if (choose(7u, 3u, 0u) != 3u ||
        choose(7u, 3u, 2u) != 3u ||
        choose(0u, 0u, 0u) != 0u ||
        choose(0u, 33u, 0u) != 33u ||
        choose(0u, 3u, 3u) != 3u)
        return false;
    GameReadbackProvenance fresh{44u, 3u, 0xabcdu, 8u};
    return fresh.may_present(44u, true) &&
           !fresh.may_present(45u, true) &&
           fresh.same_device(0xabcdu) &&
           fresh.same_output(8u) &&
           !GameNativeFramePublication::should_upload(true, false, true, 0u);
}
static_assert(native_full_frame_slot_reuse(),
              "Full game GPU readback staging continuity/fallback regression");
int main() { assert(native_full_frame_slot_reuse()); return 0; }
