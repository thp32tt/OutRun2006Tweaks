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
int main()
{
    TestHeadsetCadence(60.0);
    TestHeadsetCadence(72.0);
    TestHeadsetCadence(80.0);
    TestHeadsetCadence(90.0);
    TestHeadsetCadence(120.0);
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
    const auto disabled = Advance(1.0f, 0.0f, 1.0f, true, false);
    assert(disabled.faces == 0 && disabled.pendingFaces == 0.0f);
    return 0;
}
