// 01064: genuine sequential left/right native camera view admission.
#include "../../src/vr/d3d11/native_game_eye_pair_sources.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11;
int main() {
    constexpr std::uint32_t u=87u, s=91u, t=90u;
    constexpr auto match=native_game_eye_captured_rtv_admitted;
    assert(match(t,u,u,1,true,true,0,0,0,0,1,u,s,t));
    assert(match(t,s,s,1,true,true,1,3,1,3,1,u,s,t));
    assert(!match(t,s,u,1,true,true,0,0,0,0,1,u,s,t)); // wrong gamma
    assert(!match(t,u,u,1,false,true,0,0,0,0,1,u,s,t)); // foreign allocation
    assert(!match(t,u,u,1,true,false,0,0,0,0,1,u,s,t)); // unbound at capture
    assert(!match(t,u,u,1,true,true,1,0,0,0,1,u,s,t)); // wrong mip
    assert(!match(t,u,u,1,true,true,0,1,0,0,1,u,s,t)); // wrong eye slice
    assert(!match(t,u,u,1,true,true,0,0,0,0,2,u,s,t)); // array-wide RTV
    assert(!match(t,u,u,4,true,true,0,0,0,0,1,u,s,t)); // typeless MSAA
    assert(!match(t,0,u,1,true,true,0,0,0,0,1,u,s,t)); // untyped view
    assert(!match(28,u,u,1,true,true,0,0,0,0,1,u,s,t)); // RGBA not BGRA
    assert(match(u,u,u,1,true,true,0,0,0,0,1,u,s,t)); // exact typed source
    assert(!match(u,s,u,1,true,true,0,0,0,0,1,u,s,t)); // no gamma reinterpretation
}
