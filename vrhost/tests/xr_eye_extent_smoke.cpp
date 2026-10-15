#include "vr/ipc/xr_eye_extent.hpp"
#include "vr/ipc/coherent_host_identity.hpp"
#include "runtime/fallback_projection_extent.hpp"
#include <iostream>
#include <cstdint>
#include <limits>
using namespace OutRunVR::EyeExtent;
#define REQUIRE(x) do { if (!(x)) { std::cerr << "eye extent check failed line " << __LINE__ << "\n"; return 1; } } while (false)
int main(int argc, char** argv)
{
    const bool resetTest = argc > 1 && argv[1][0] == '-' && argv[1][2] == 'r';
    const ViewLimits l{{2016,2240},{4096,4096}};
    const ViewLimits r{{2124,2284},{3072,3000}};
    const Size nominal = ResolveHost(l, r, 1.0f);
    REQUIRE(Equal(nominal, {2124,2284}));
    // R19 classic-SBS fallback must allocate for both array-swapchain views.
    using OutRunVrFallbackProjectionExtent::Resolve;
    const auto fallback = Resolve(2016, 2208, 2124, 2284);
    REQUIRE(fallback.Valid() && fallback.width == 2124 && fallback.height == 2284);
    const auto swapped = Resolve(2124, 2284, 2016, 2208);
    REQUIRE(swapped.Valid() && swapped.width == fallback.width &&
        swapped.height == fallback.height);
    const auto mixed = Resolve(1800, 2400, 2000, 2000);
    REQUIRE(mixed.Valid() && mixed.width == 2000 && mixed.height == 2400);
    REQUIRE(!Resolve(2016, 2208, 0, 2208).Valid());
    REQUIRE(!Resolve(-1, 2208, 2016, 2208).Valid());
    REQUIRE(!Resolve(2016, 2208, 8193, 2208).Valid());

    REQUIRE(Equal(ResolveHost(l,r,1.5f), {3072,3000}));
    REQUIRE(Equal(ResolveHost(l,r,0.5f), {1062,1142}));
    REQUIRE(!Valid(ResolveHost({{0,2240},{4096,4096}},r,1)));
    REQUIRE(!Valid(ResolveHost(l,r,std::numeric_limits<float>::infinity())));
    REQUIRE(!Valid(ResolveHost(l,r,0)));
    REQUIRE(Equal(ResolveGame(nominal,{8192,8192}), nominal));
    REQUIRE(!Valid(ResolveGame(nominal,{2048,4096})));
    REQUIRE(!Valid(ResolveGame({0,2284},{4096,4096})));
    REQUIRE(!Valid(ResolveGame({9000,1},{10000,10000})));
    Generation generation;
    REQUIRE(generation.NeedsAllocation(nominal));
    REQUIRE(!generation.Matches(nominal));
    // A failing allocation must leave the previous generation untouched.
    generation.Commit(nominal);
    const auto first = generation.Number();
    REQUIRE(generation.Matches(nominal) && !generation.NeedsAllocation(nominal));
    const auto changed = ResolveHost(l,r,1.5f);
    REQUIRE(generation.NeedsAllocation(changed));
    REQUIRE(generation.Matches(nominal) && generation.Number() == first);
    generation.Commit(changed);
    REQUIRE(generation.Matches(changed) && generation.Number() != first);
    generation.Reset(); // Device loss / ResetEx invalidates the extent.
    REQUIRE(!Valid(generation.Active()) && generation.NeedsAllocation(changed));
    REQUIRE(!generation.Matches(changed));
    // A game-adapter cap reduction must fail closed, not resize behind XR.
    REQUIRE(!Valid(ResolveGame(changed, {2048,2048})));
    // DirectGPU identity is a single HostState.v2 seqlock publication, not
    // independent PID/LUID reads that can mix two host process generations.
    OutRunVR::SharedPoseState state{};
    state.magic = OutRunVR::SharedMagic;
    state.protocolVersion = OutRunVR::SharedProtocolVersion;
    state.structSize = sizeof(state);
    state.sequence = 2;
    state.hostPid = 101;
    state.flags = OutRunVR::HostAlive | OutRunVR::HostAdapterLuidValid;
    state.hostAdapterLuidLow = 0x111;
    state.hostAdapterLuidHigh = 0x222;
    OutRunVR::HostIdentity::Snapshot identity{};
    auto noopBarrier = []() noexcept {};
    REQUIRE(OutRunVR::HostIdentity::TryRead(&state, identity, noopBarrier));
    REQUIRE(identity.hostPid == 101 && identity.adapterLuidLow == 0x111 &&
        identity.adapterLuidHigh == 0x222);
    REQUIRE(!OutRunVR::HostIdentity::TryRead(
        nullptr, identity, noopBarrier));
    REQUIRE(identity.hostPid == 0 && identity.adapterLuidLow == 0);
    state.sequence = 3; // Writer in progress: no half-published identity.
    REQUIRE(!OutRunVR::HostIdentity::TryRead(&state, identity, noopBarrier));
    REQUIRE(identity.hostPid == 0);
    state.sequence = 4;
    bool reconnected = false;
    auto publishDuringRead = [&]() noexcept {
        if (!reconnected)
        {
            reconnected = true;
            state.sequence = 5;
            state.hostPid = 202;
            state.hostAdapterLuidLow = 0x333;
            state.hostAdapterLuidHigh = 0x444;
            state.sequence = 6;
        }
    };
    // First attempt is torn; retry returns only the completed NEW host.
    REQUIRE(OutRunVR::HostIdentity::TryRead(
        &state, identity, publishDuringRead));
    REQUIRE(identity.hostPid == 202 && identity.adapterLuidLow == 0x333 &&
        identity.adapterLuidHigh == 0x444);
    // A continuously racing writer cannot cause a partial identity to leak.
    auto unstableBarrier = [&]() noexcept { ++state.sequence; };
    REQUIRE(!OutRunVR::HostIdentity::TryRead(
        &state, identity, unstableBarrier));
    REQUIRE(identity.hostPid == 0 && identity.adapterLuidHigh == 0);
    state.sequence = 8;
    state.flags = OutRunVR::HostAdapterLuidValid;
    REQUIRE(!OutRunVR::HostIdentity::TryRead(&state, identity, noopBarrier));
    state.flags |= OutRunVR::HostAlive;
    state.hostPid = 0;
    REQUIRE(!OutRunVR::HostIdentity::TryRead(&state, identity, noopBarrier));
    state.hostPid = 202;
    state.protocolVersion = 0;
    REQUIRE(!OutRunVR::HostIdentity::TryRead(&state, identity, noopBarrier));
    state.protocolVersion = OutRunVR::SharedProtocolVersion;
    state.structSize = 0;
    REQUIRE(!OutRunVR::HostIdentity::TryRead(&state, identity, noopBarrier));
    state.structSize = sizeof(state);
    REQUIRE(OutRunVR::HostIdentity::TryRead(&state, identity, noopBarrier));
    std::cout << (resetTest ? "XR-EYE-RESET" : "XR-EYE-SIZING")
              << " PASS: runtime extent, shared-slice limits, cap failure and reset\n";
    return 0;
}
