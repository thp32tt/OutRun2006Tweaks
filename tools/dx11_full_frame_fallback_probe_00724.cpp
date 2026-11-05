#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_readback_provenance.hpp"
#include <cassert>
#include <cstdint>

using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
using outrun::vr::dx11::live_game_frame::GameReadbackProvenance;

int main() {
    GameNativeFrameBatch frame{};
    GameReadbackProvenance prior{};
    std::uint64_t generation = 11u;
    prior.sourceDraws = 2u;
    prior.sourceDevice = 0x123u;
    prior.outputGeneration = generation;
    prior.capturedAtPresent = 40u;
    assert(prior.may_overlay(41u) && prior.same_output(generation));

    // Source scene composed by a complete menu/race Draw+DrawIndexed pair.
    for (std::uint64_t ordinal = 0u; ordinal < 2u; ++ordinal) {
        assert(frame.accepts_full(ordinal));
        frame.succeeded(false);
        frame.record_source_draw(ordinal);
    }
    assert(frame.publishable_full(true, 2u));
    assert(!GameReadbackProvenance::quarantine_full_frame(
        true, frame.publishable_full(true, 2u), true));

    // Next game's source contains a missing/unsupported Draw. It cannot
    // inherit the old full-frame GPU result, including not-ready fences.
    frame.reset();
    assert(frame.accepts_full(0u));
    frame.succeeded(false);
    frame.record_source_draw(0u);
    frame.abort();
    assert(!frame.publishable_full(true, 2u));
    assert(GameReadbackProvenance::quarantine_full_frame(
        true, frame.publishable_full(true, 2u), true));
    ++generation;
    assert(!prior.same_output(generation));

    // Presentation rejected by crop/dirty/backbuffer checks also fences
    // queued full-frame results, but not legacy asynchronous inset samples.
    assert(GameReadbackProvenance::quarantine_full_frame(true, true, false));
    assert(!GameReadbackProvenance::quarantine_full_frame(false, false, false));
    assert(!GameReadbackProvenance::quarantine_full_frame(false, true, true));
    assert(!prior.may_overlay(43u));
    return 0;
}
