// Live menu -> car selection -> race CPU/GDI full-backbuffer burst replay.
// A readback is full-sized even if UpdateSurface/StretchRect dirtied 1 pixel.
#include "../src/vr/d3d11/native_game_surface_replay_budget.hpp"
#include <cassert>
#include <cstdint>
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceReplayBudget;
int main() {
    using B = GameNativeSurfaceReplayBudget;
    static_assert(B::full_readback_bytes(1920,1080) == 8294400u);
    static_assert(B::full_readback_bytes(3440,1440) == 19814400u);
    static_assert(B::full_readback_bytes(0,1080) == 0u);
    static_assert(B::full_readback_bytes(65536,65536) == 0u);
    B live{};
    // More than eight genuine 1080p backbuffer edits can precede first
    // native Draw. Every edit gets a fresh canonical full-image snapshot.
    for (std::uint32_t i=0; i<32u; ++i) {
        assert(live.admits(1920,1080));
        live.note_success(1920,1080);
    }
    assert(live.operations == 32u);
    assert(!live.admits(1920,1080)); // full readback bandwidth exhausted
    const auto fixedCount = live.operations, fixedBytes = live.bytes;
    live.note_success(1920,1080);
    assert(live.operations == fixedCount && live.bytes == fixedBytes);
    // Present, Reset and authenticated new full Clear begin a fresh source
    // epoch. The original fallback never requires a native snapshot.
    live.reset();
    assert(live.operations == 0u && live.bytes == 0u);
    for (std::uint32_t i=0u; i<8u; ++i) {
        assert(live.admits(3840,2160));
        live.note_success(3840,2160);
    }
    assert(!live.admits(3840,2160));
    live.reset();
    assert(live.admits(3440,1440)); // resolution Reset and cold first Draw
    live.note_success(3440,1440);
    assert(live.admits(1920,1080)); // budget uses each actual source extent
    assert(!live.admits(65536,65536));
    B runaway{};
    for (std::uint32_t i=0u;i<B::kMaxOperations;++i) {
        assert(runaway.admits(1,1));
        runaway.note_success(1,1);
    }
    assert(!runaway.admits(1,1)); // reject pathological repeated tiny reads
}
