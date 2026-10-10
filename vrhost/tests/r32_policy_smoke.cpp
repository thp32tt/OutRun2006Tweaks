#include "vr/d3d9/r32_policy.hpp"

// Return a nonzero exit code even in Release/NDEBUG builds. The previous
// R32_CHECK() checks were compiled out in the Windows CI Release configuration.
#define R32_CHECK(expression) do { if (!(expression)) return __LINE__; } while (false)
#include <cstdint>
#include <limits>

int main()
{
    using namespace OutRunVR::R32;

    // Reset after a long run must not retain an old absolute mono-safety epoch.
    R32_CHECK(RearmMonoSafetyEpoch(1) == 3);
    R32_CHECK(RearmMonoSafetyEpoch(42, 2) == 44);
    R32_CHECK(RearmMonoSafetyEpoch(0, 2) == 3);

    const auto maxValue = (std::numeric_limits<std::uint64_t>::max)();
    R32_CHECK(RearmMonoSafetyEpoch(maxValue - 1, 4) == maxValue);

    R32_CHECK(EffectSnapshotResult(true) ==
        EffectSnapshotDecision::UseCapturedPolicy);
    R32_CHECK(EffectSnapshotResult(false) ==
        EffectSnapshotDecision::ForceZeroDisparity);

    // Frame-spike diagnostics adapt to the observed baseline instead of
    // assuming a fixed HMD refresh rate.
    R32_CHECK(!IsPerfFrameSpike(14000, 12000));
    R32_CHECK(IsPerfFrameSpike(18000, 12000));
    R32_CHECK(!IsPerfFrameSpike(18000, 17000));
    R32_CHECK(IsPerfFrameSpike(30000, 25000));
    R32_CHECK(UpdatePerfBaselineUs(0, 12000, false) == 12000);
    R32_CHECK(UpdatePerfBaselineUs(12000, 30000, true) == 12000);
    R32_CHECK(UpdatePerfBaselineUs(12000, 15200, false) == 12100);
    // Adversarial QPC values must not wrap the relative spike RHS or EMA.
    R32_CHECK(!IsPerfFrameSpike(18000, maxValue));
    R32_CHECK(IsPerfFrameSpike(30000, maxValue));
    R32_CHECK(UpdatePerfBaselineUs(maxValue, maxValue - 31, false) == maxValue - 1);
    R32_CHECK(UpdatePerfBaselineUs(maxValue - 31, maxValue, false) == maxValue - 31);
    R32_CHECK(UpdatePerfBaselineUs(maxValue - 320, maxValue, false) == maxValue - 310);
    R32_CHECK(UpdatePerfBaselineUs(12000, 11999, false) == 11999);
    R32_CHECK(UpdatePerfBaselineUs(12000, 12031, false) == 12000);


    return 0;
}
