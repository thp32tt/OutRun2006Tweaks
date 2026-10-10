#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>

#include "vr/ipc/host_pose_v3.hpp"

using namespace OutRunVR::IpcV3;

namespace
{
    HostState MakeValid()
    {
        HostState state{};
        InitializeWireState(state);
        state.hostPid = 42;
        state.flags = HostAlive | OrientationValid | PositionValid |
            SessionVisible | SessionFocused | StereoViewsValid | HostShouldRender;
        state.poseId = 1234;
        state.sampleQpc = 9'950'000;
        state.headOrientation[3] = 1.0f;
        state.headPositionMeters[0] = 1.0f;
        state.headPositionMeters[1] = 2.0f;
        state.headPositionMeters[2] = 3.0f;
        for (int eye = 0; eye < 2; ++eye)
        {
            state.eyes[eye].orientation[3] = 1.0f;
            state.eyes[eye].positionMeters[0] = eye == 0 ? -0.032f : 0.032f;
            state.eyes[eye].fov.angleLeft = -0.8f;
            state.eyes[eye].fov.angleRight = 0.8f;
            state.eyes[eye].fov.angleUp = 0.9f;
            state.eyes[eye].fov.angleDown = -0.9f;
        }
        return state;
    }

    bool Expect(bool condition, const char* name)
    {
        if (!condition)
            std::cerr << "FAILED: " << name << '\n';
        return condition;
    }
}

int main()
{
    constexpr std::int64_t now = 10'000'000;
    constexpr std::int64_t frequency = 1'000'000;
    bool ok = true;

    auto state = MakeValid();
    ok &= Expect(HostStateUsable(state, now, frequency), "valid pose accepted");

    state = MakeValid();
    state.sampleQpc = now - frequency;
    ok &= Expect(!HostStateUsable(state, now, frequency), "stale pose rejected");

    // Inclusive age boundary and fractional QPC ticks-per-millisecond.
    state = MakeValid();
    state.sampleQpc = now - 250'000;
    ok &= Expect(HostStateUsable(state, now, frequency), "250 ms boundary accepted");
    state.sampleQpc = now - 250'001;
    ok &= Expect(!HostStateUsable(state, now, frequency), "250 ms plus one tick rejected");

    state = MakeValid();
    state.sampleQpc = now - 250;
    ok &= Expect(HostStateUsable(state, now, 1001), "fractional QPC cutoff accepted");
    state.sampleQpc = now - 251;
    ok &= Expect(!HostStateUsable(state, now, 1001), "fractional QPC stale rejected");

    // Old (frequency * staleMilliseconds) overflowed int64.
    constexpr auto maxQpc = std::numeric_limits<std::int64_t>::max();
    state = MakeValid();
    state.sampleQpc = 1;
    ok &= Expect(HostStateUsable(state, maxQpc, maxQpc, 1000),
        "int64 limit at one-second cutoff accepted");
    ok &= Expect(HostStateUsable(state, maxQpc, maxQpc, maxQpc),
        "int64 frequency and tolerance accepted without wrap");
    ok &= Expect(!HostStateUsable(state, maxQpc, 1, maxQpc),
        "int64 tolerance cannot admit stale sample");

    state = MakeValid();
    state.sampleQpc = now + 1;
    ok &= Expect(!HostStateUsable(state, now, frequency), "future QPC sample rejected");
    ok &= Expect(!HostStateUsable(state, -1, frequency), "negative now QPC rejected");

    state = MakeValid();
    state.headOrientation[0] = std::nanf("");
    ok &= Expect(!HostStateUsable(state, now, frequency), "NaN quaternion rejected");

    state = MakeValid();
    state.eyes[0].positionMeters[0] = -0.5f;
    ok &= Expect(!HostStateUsable(state, now, frequency), "implausible eye offset rejected");

    state = MakeValid();
    state.eyes[1].fov.angleRight = state.eyes[1].fov.angleLeft + 0.01f;
    ok &= Expect(!HostStateUsable(state, now, frequency), "degenerate FOV rejected");

    state = MakeValid();
    state.flags &= ~HostShouldRender;
    ok &= Expect(!HostStateUsable(state, now, frequency), "non-renderable host rejected");

    state = MakeValid();
    state.flags &= ~StereoViewsValid;
    ok &= Expect(HostStateUsable(state, now, frequency), "mono-valid pose remains usable");

    // Invalid optional fields must never reach an otherwise valid published
    // game-side snapshot (including NaNs in unflagged wire state fields).
    state = MakeValid();
    auto candidate = SnapshotFromValidatedHostState(state);
    ok &= Expect(candidate.poseId == state.poseId && candidate.hostPid == state.hostPid &&
        candidate.referenceSpaceGeneration == state.referenceSpaceGeneration &&
        candidate.positionValid && candidate.stereoValid &&
        candidate.headPositionMeters[0] == 1.0f &&
        candidate.eyes[1].positionMeters[0] == 0.032f,
        "validated stereo and position fields copied");

    state.flags &= ~(PositionValid | StereoViewsValid);
    state.headPositionMeters[0] = std::numeric_limits<float>::quiet_NaN();
    state.eyes[0].orientation[0] = std::numeric_limits<float>::quiet_NaN();
    ok &= Expect(HostStateUsable(state, now, frequency),
        "absent optional field poison does not invalidate valid head pose");
    candidate = SnapshotFromValidatedHostState(state);
    ok &= Expect(!candidate.positionValid && !candidate.stereoValid &&
        candidate.headPositionMeters[0] == 0.0f &&
        candidate.headPositionMeters[1] == 0.0f &&
        candidate.eyes[0].orientation[0] == 0.0f &&
        candidate.eyes[1].positionMeters[0] == 0.0f &&
        candidate.headOrientation[3] == 1.0f,
        "absent optional position/eyes sanitized before publication");

    if (!ok)
        return 1;
    std::cout << "HostState.v3 pose validation rules passed.\n";
    return 0;
}
