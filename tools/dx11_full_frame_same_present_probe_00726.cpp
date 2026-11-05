#include "../src/vr/d3d11/native_game_readback_provenance.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool same_present_frame_contract() {
    GameReadbackProvenance frame{40u, 2u, 0x123u, 3u};
    if (!frame.may_present(40u, true) || frame.may_present(41u, true) ||
        frame.may_present(42u, true) || frame.may_present(39u, true))
        return false;
    if (frame.may_overlay(40u) || !frame.may_overlay(41u) ||
        !frame.may_overlay(42u) || frame.may_overlay(43u))
        return false;
    if (!frame.may_present(41u, false) || frame.may_present(40u, false))
        return false;
    if (!frame.same_device(0x123u) || !frame.same_output(3u) ||
        frame.same_device(0x124u) || frame.same_output(4u))
        return false;
    frame.sourceDraws = 0u;
    if (frame.may_present(40u, true) || frame.may_present(41u, false))
        return false;
    GameNativeFrameBatch batch{};
    for (std::uint64_t i = 0; i < 2u; ++i) {
        if (!batch.accepts_full(i)) return false;
        batch.succeeded(false);
        batch.record_source_draw(i);
    }
    if (!batch.publishable_full(true, 2u) ||
        GameReadbackProvenance::quarantine_full_frame(true, true, true))
        return false;
    batch.abort();
    return !batch.publishable_full(true, 2u) &&
        GameReadbackProvenance::quarantine_full_frame(true, false, true);
}
static_assert(same_present_frame_contract(), "No lagged full game frame");
int main() { assert(same_present_frame_contract()); return 0; }
