#include "vr/ipc/native_geometry_backbuffer.hpp"
#include <iostream>
#include <cstdint>
using namespace OutRunVR::EyeExtent;
#define CHECK(p) do { if (!(p)) { std::cerr << "native geometry failure line " << __LINE__ << "\n"; return 1; } } while(false)
int main()
{
    const Size game{3440,1440}, xr{2124,2284}, caps{8192,8192};
    const auto up = ResolveNativeBackbuffer(game,xr,caps,true);
    CHECK(up.changed);
    CHECK(up.dimensions.height==2284);
    CHECK(up.dimensions.width>=xr.width && up.dimensions.height>=xr.height);
    CHECK(static_cast<std::uint64_t>(up.dimensions.width)*game.height >=
          static_cast<std::uint64_t>(game.width)*up.dimensions.height);
    CHECK(static_cast<std::uint64_t>(up.dimensions.width)*up.dimensions.height<=16000000);
    // Must not silently pretend smaller game pixels are a native XR source.
    CHECK(!Valid(ResolveNativeBackbuffer(game,xr,{4096,4096},true).dimensions));
    CHECK(!Valid(ResolveNativeBackbuffer(game,xr,caps,false).dimensions));
    CHECK(!Valid(ResolveNativeBackbuffer(game,{0,2284},caps,true).dimensions));
    CHECK(!Valid(ResolveNativeBackbuffer(game,xr,caps,true,2000000).dimensions));
    CHECK(!Valid(ResolveNativeBackbuffer({0,1440},xr,caps,true).dimensions));
    const auto match=ResolveNativeBackbuffer({2280,2460},{2124,2284},caps,true);
    CHECK(!match.changed && Equal(match.dimensions,{2280,2460}));
    const auto wide=ResolveNativeBackbuffer(game,{6000,1100},caps,true);
    CHECK(Valid(wide.dimensions) && wide.dimensions.width>=6000);
    CHECK(!Valid(ResolveNativeBackbuffer(game,{9000,1100},caps,true).dimensions));
    std::cout<<"XR-NATIVE-GEOMETRY pass: supersampled D3D9 geometry source, fail-closed caps\n";
}
