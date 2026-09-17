#include "vr/d3d9/r32_policy.hpp"

#include <cassert>
#include <cstdint>
#include <limits>

int main()
{
    using namespace OutRunVR::R32;

    // Regression: a Reset after a long run must not retain the old absolute
    // R29MonoSafetyThroughEpoch. PresentEpoch is reset to 1, so the new horizon
    // is always local to the reset generation.
    assert(RearmMonoSafetyEpoch(1) == 3);
    assert(RearmMonoSafetyEpoch(42, 2) == 44);
    assert(RearmMonoSafetyEpoch(0, 2) == 3);

    const auto maxValue = (std::numeric_limits<std::uint64_t>::max)();
    assert(RearmMonoSafetyEpoch(maxValue - 1, 4) == maxValue);

    assert(EffectSnapshotResult(true) ==
        EffectSnapshotDecision::UseCapturedPolicy);
    assert(EffectSnapshotResult(false) ==
        EffectSnapshotDecision::ForceZeroDisparity);

    static_assert(ProducerFenceBudgetMs <= 2,
        "R32 producer fence must stay below the old 12 ms synchronous budget");
    return 0;
}
