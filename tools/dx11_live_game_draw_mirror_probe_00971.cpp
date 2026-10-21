#include "../src/vr/d3d11/live_game_draw_mirror_cache.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame::draw_mirror_cache;
constexpr int a=1, b=2;
constexpr ViewKey same{&a,false,true}, alias{&a,false,true};
constexpr ViewKey gamma{&a,true,true}, base{&a,false,false};
constexpr ViewKey other{&b,false,true}, empty{};
static_assert(same_view(same,alias));
static_assert(!same_view(same,gamma));
static_assert(!same_view(same,base));
static_assert(!same_view(same,other));
static_assert(!same_view(empty,empty));
int main() {
    assert(same_view(same,alias));
    assert(!same_view(same,gamma));
    assert(!same_view(same,base));
    assert(!same_view(same,other));
}
