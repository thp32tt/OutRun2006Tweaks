// Standalone regression: c++ -std=c++17 -Wall -Wextra -pedantic
// tests/native_raw_source_probe_schedule_test.cpp -o /tmp/raw_probe_test
#include "../src/vr/d3d11/native_game_raw_source_probe.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::NativeRawSourceProbeSchedule;
int main() {
    NativeRawSourceProbeSchedule probe;
    assert(probe.should_attempt(0u, 0u));
    assert(!probe.should_attempt(0u, 5u));
    assert(probe.should_attempt(320u, 5u));
    probe.record_attempt(320u);
    assert(probe.attempts() == 1u);
    assert(!probe.should_attempt(415u, 5u));
    assert(probe.should_attempt(416u, 5u));
    for (std::uint64_t i = 1u; i < 4u; ++i) {
        const auto ordinal = probe.next_ordinal();
        assert(probe.should_attempt(ordinal, 5u));
        probe.record_attempt(ordinal);
    }
    assert(probe.attempts() == NativeRawSourceProbeSchedule::kMaxAttemptsPerFrame);
    assert(!probe.should_attempt(200000u, 5u));
    probe.reset();
    assert(probe.attempts() == 0u);
    assert(probe.should_attempt(0u, 24u));
    const auto max = (std::numeric_limits<std::uint64_t>::max)();
    probe.record_attempt(max - 4u);
    assert(probe.next_ordinal() == max);
    assert(!probe.should_attempt(max - 1u, 0u));
    assert(probe.should_attempt(max, 0u));
    // Previous real game's 2,400 Draws are sampled across the entire
    // source population, not only a fixed first-1,536-Draw window.
    probe.reset();
    probe.finish_present(2400u);
    assert(probe.previous_source_draws() == 2400u);
    assert(!probe.should_attempt(499u, 5u));
    assert(probe.should_attempt(500u, 5u));
    probe.record_attempt(500u);
    assert(!probe.should_attempt(595u, 5u));
    assert(probe.should_attempt(596u, 5u));
    probe.restart_epoch(); // genuine full Clear: retain previous Present
    assert(probe.attempts() == 0u && probe.previous_source_draws() == 2400u);
    assert(!probe.should_attempt(1199u, 12u));
    assert(probe.should_attempt(1200u, 12u));
    probe.finish_present(3u);
    assert(!probe.should_attempt(1u, 23u));
    assert(probe.should_attempt(2u, 23u));
    probe.finish_present(max); // saturating epoch must never wrap
    assert(probe.should_attempt(max - 1u, 23u));
    probe.reset();
    assert(probe.previous_source_draws() == 0u);
    assert(probe.should_attempt(320u, 5u)); // device reset fallback
    return 0;
}
