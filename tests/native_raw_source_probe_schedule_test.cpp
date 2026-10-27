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
    return 0;
}
