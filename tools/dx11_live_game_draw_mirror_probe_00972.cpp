#include "../src/vr/d3d11/live_game_draw_mirror_cache.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame::draw_mirror_cache;
constexpr int twoD=1, cube=2;
constexpr ViewKey psCube{&cube,false,true,true}, vsCube{&cube,false,true,true};
constexpr ViewKey otherGamma{&cube,true,true,true}, otherMip{&cube,false,false,true};
constexpr ViewKey otherSource{&twoD,false,true,true}, dimensionMismatch{&cube,false,true,false};
constexpr ViewKey ps2d{&twoD,false,true,false}, vs2d{&twoD,false,true,false};
constexpr ViewKey emptyCube{nullptr,false,true,true};
static_assert(same_view(psCube,vsCube),"VS+PS share game-authored cube");
static_assert(same_view(ps2d,vs2d),"2D view remains shared");
static_assert(!same_view(psCube,otherGamma),"do not merge sRGB");
static_assert(!same_view(psCube,otherMip),"do not merge mip generation");
static_assert(!same_view(psCube,otherSource),"do not merge images");
static_assert(!same_view(psCube,dimensionMismatch),"cube cannot alias 2D");
static_assert(!same_view(emptyCube,emptyCube),"missing image rejected");
int main(){assert(same_view(psCube,vsCube));assert(!same_view(psCube,dimensionMismatch));}
