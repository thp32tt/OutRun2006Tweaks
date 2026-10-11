#include "vr/ipc/xr_eye_extent.hpp"
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
    std::cout << (resetTest ? "XR-EYE-RESET" : "XR-EYE-SIZING")
              << " PASS: runtime extent, shared-slice limits, cap failure and reset\n";
    return 0;
}
