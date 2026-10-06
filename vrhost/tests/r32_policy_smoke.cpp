#include "vr/d3d9/r32_policy.hpp"

#include <cassert>
#include <cstdint>
#include <limits>

int main()
{
    using namespace OutRunVR::R32;

    // Reset after a long run must not retain an old absolute mono-safety epoch.
    assert(RearmMonoSafetyEpoch(1) == 3);
    assert(RearmMonoSafetyEpoch(42, 2) == 44);
    assert(RearmMonoSafetyEpoch(0, 2) == 3);

    const auto maxValue = (std::numeric_limits<std::uint64_t>::max)();
    assert(RearmMonoSafetyEpoch(maxValue - 1, 4) == maxValue);

    assert(EffectSnapshotResult(true) ==
        EffectSnapshotDecision::UseCapturedPolicy);
    assert(EffectSnapshotResult(false) ==
        EffectSnapshotDecision::ForceZeroDisparity);

    // Frame-spike diagnostics adapt to the observed baseline instead of
    // assuming a fixed HMD refresh rate.
    assert(!IsPerfFrameSpike(14000, 12000));
    assert(IsPerfFrameSpike(18000, 12000));
    assert(!IsPerfFrameSpike(18000, 17000));
    assert(IsPerfFrameSpike(30000, 25000));
    assert(UpdatePerfBaselineUs(0, 12000, false) == 12000);
    assert(UpdatePerfBaselineUs(12000, 30000, true) == 12000);
    assert(UpdatePerfBaselineUs(12000, 15200, false) == 12100);

    return 0;
}
