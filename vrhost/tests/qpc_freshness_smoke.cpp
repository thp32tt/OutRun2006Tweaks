#include "../../src/vr/ipc/qpc_freshness.hpp"
#include <cassert>
#include <cstdint>
#include <limits>

int main()
{
    using OutRunVR::Ipc::ElapsedQpcMilliseconds;
    constexpr std::int64_t ghz = 3'000'000'000LL;
    constexpr std::int64_t sample = 100LL;
    assert(ElapsedQpcMilliseconds(sample, sample, ghz) == 0);
    assert(ElapsedQpcMilliseconds(sample, sample + ghz, ghz) == 1000);
    assert(ElapsedQpcMilliseconds(sample, sample + ghz * 3 / 2, ghz) == 1500);
    assert(ElapsedQpcMilliseconds(sample, sample + ghz * 40LL * 86400LL, ghz) ==
        40LL * 86400LL * 1000LL); // Old ticks*1000 wraps a signed int64.
    assert(ElapsedQpcMilliseconds(sample, sample + 999'999, 1'000'000) == 999);
    assert(ElapsedQpcMilliseconds(sample, sample - 1, ghz) == -1);
    assert(ElapsedQpcMilliseconds(0, sample, ghz) == -1);
    assert(ElapsedQpcMilliseconds(sample, sample, 0) == -1);
    assert(ElapsedQpcMilliseconds(1, (std::numeric_limits<std::int64_t>::max)(), 1) ==
        (std::numeric_limits<std::int64_t>::max)());
    const auto high = (std::numeric_limits<std::int64_t>::max)() / 2 - 1;
    assert(ElapsedQpcMilliseconds(1, 1 + high / 2, high) == 500);
    // Above INT64_MAX/1000, old floating point fallback rounded the value
    // immediately below a millisecond boundary up to the next millisecond.
    constexpr std::int64_t huge = 9'000'000'000'000'000'000LL;
    assert(ElapsedQpcMilliseconds(1, 1 + huge / 500 - 1, huge) == 1);
    assert(ElapsedQpcMilliseconds(1, 1 + huge / 500, huge) == 2);
    assert(ElapsedQpcMilliseconds(1, huge, huge) == 999);
}
