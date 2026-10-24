// Portable source-level regression for OutRun 2006 R84 reflection pacing.
// Run: c++ -std=c++17 -O2 -Wall -Wextra -Isrc tools/test_vr_reflection_frame_budget.cpp -o /tmp/r84-reflect && /tmp/r84-reflect
#include "../src/vr/game/reflection_frame_budget.hpp"
#include <cassert>
#include <cmath>
#include <limits>
using OutRunVR::ReflectionFrameBudget::AdaptiveFrameCadence;
using OutRunVR::ReflectionFrameBudget::Advance;

static void TestHeadsetCadence(double hz)
{
    AdaptiveFrameCadence cadence;
    const double period = 1.0 / hz;
    for (int i = 0; i < 24; ++i)
        assert(!cadence.Observe(period));
    assert(!cadence.Observe(period * (hz == 60.0 ? 1.05 : 1.10))); // nonlate cadence jitter
    if (hz == 60.0)
        assert(cadence.Observe(period * 1.10)); // preserve legacy >18ms limit
    if (hz >= 90.0)
        assert(cadence.Observe(period * 1.40)); // missed XR deadline <18 ms
    assert(cadence.Observe(0.022));             // legacy >18 ms protection
    assert(!cadence.Observe(period));           // recovery does not retain debt
}

static void TestSlowerRefreshRelock(double beforeHz, double afterHz)
{
    AdaptiveFrameCadence cadence;
    for (int i = 0; i < 30; ++i)
        assert(!cadence.Observe(1.0 / beforeHz));
    for (int i = 0; i < 23; ++i)
        assert(cadence.Observe(1.0 / afterHz));
    // Only a continuous nominal series is allowed to re-lock, not a
    // single GPU-late frame. First normal-budget frame is sample 24.
    assert(!cadence.Observe(1.0 / afterHz));
    assert(!cadence.Observe(1.0 / afterHz));
    assert(cadence.Observe(0.025));
    assert(!cadence.Observe(1.0 / afterHz));
}

static void TestLateGpuFramesNeverTrainRefresh()
{
    AdaptiveFrameCadence cadence;
    for (int i = 0; i < 30; ++i)
        assert(!cadence.Observe(1.0 / 120.0));
    // A persistently overloaded but noncanonical 12ms 120Hz frame is late.
    for (int i = 0; i < 64; ++i)
        assert(cadence.Observe(0.012));
    // Interleaving a recovered 120Hz frame or a loading gap invalidates a
    // partial 72Hz candidate; the next 72Hz frame is still protected.
    for (int i = 0; i < 18; ++i)
        assert(cadence.Observe(1.0 / 72.0));
    assert(!cadence.Observe(1.0 / 120.0));
    for (int i = 0; i < 23; ++i)
        assert(cadence.Observe(1.0 / 72.0));
    assert(cadence.Observe(0.150));
    assert(cadence.Observe(1.0 / 72.0));
    cadence.Reset(); // VR disabled, restart or lost timing source.
    assert(!cadence.Observe(1.0 / 72.0));
}

int main()
{
    TestHeadsetCadence(60.0);
    TestHeadsetCadence(72.0);
    TestHeadsetCadence(80.0);
    TestHeadsetCadence(90.0);
    TestHeadsetCadence(120.0);
    TestSlowerRefreshRelock(120.0, 90.0);
    TestSlowerRefreshRelock(120.0, 80.0);
    TestSlowerRefreshRelock(120.0, 72.0);
    TestSlowerRefreshRelock(120.0, 60.0);
    TestSlowerRefreshRelock(90.0, 72.0);
    TestLateGpuFramesNeverTrainRefresh();
    AdaptiveFrameCadence cadence;
    for (int i = 0; i < 8; ++i) assert(!cadence.Observe(1.0 / 120.0));
    assert(cadence.Observe(0.012)); // 120-Hz missed frame; old 18-ms gate missed
    assert(cadence.Observe(0.100)); // long load does not retrain cadence
    assert(cadence.Observe(0.012));
    assert(!cadence.Observe(1.0 / 120.0));
    assert(!cadence.Observe(std::numeric_limits<double>::quiet_NaN()));
    for (int i = 0; i < 4; ++i) assert(!cadence.Observe(1.0 / 72.0));
    assert(!cadence.Observe(1.0 / 72.0));
    cadence.Reset();
    assert(!cadence.Observe(1.0 / 60.0));

    // An on-time 120-Hz R84 frame keeps the exact original 0.5-rate,
    // 180-faces-per-second budget, without changing content fidelity.
    float pending = 0.0f;
    int faces = 0;
    for (int i = 0; i < 120; ++i)
    {
        const auto r = Advance(pending, 0.5f, 0.5f, true, false);
        pending = r.pendingFaces;
        assert(r.faces >= 0 && r.faces <= 3);
        faces += r.faces;
    }
    assert(faces == 180);
    const auto late = Advance(0.75f, 0.5f, 2.0f, true, true);
    assert(late.faces <= 2 && late.pendingFaces <= 1.0f);
    // Review-only A/B: the healthy 120 Hz 180-face budget stays identical.
    const auto normal = Advance(0.0f, 0.5f, 0.5f, true, false, false);
    const auto optNormal = Advance(0.0f, 0.5f, 0.5f, true, false, true);
    assert(normal.faces == optNormal.faces);
    assert(normal.pendingFaces == optNormal.pendingFaces);
    // A late GPU frame no longer requests the same amount of cubemap work
    // when the isolated review option is enabled.
    const auto originalLate = Advance(0.0f, 0.5f, 0.5f, true, true, false);
    const auto optedLate = Advance(0.0f, 0.5f, 0.5f, true, true, true);
    assert(originalLate.faces == 1);
    assert(optedLate.faces == 0);
    assert(optedLate.pendingFaces > originalLate.pendingFaces && optedLate.pendingFaces < 1.0f);
    // No effect outside VR-normalized mode; malformed configuration and
    // disabling reflection still clear debt on both variants.
    const auto desktopA = Advance(0.0f, 0.5f, 1.0f, false, true, false);
    const auto desktopB = Advance(0.0f, 0.5f, 1.0f, false, true, true);
    assert(desktopA.faces == desktopB.faces);
    assert(Advance(1.0f, 0.0f, 0.5f, true, true, true).faces == 0);
    const auto disabled = Advance(1.0f, 0.0f, 1.0f, true, false);
    assert(disabled.faces == 0 && disabled.pendingFaces == 0.0f);
    return 0;
}
