#include "../../src/vr/d3d9/r30_indexed_up_bounds.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using namespace OutRunVR::R30IndexedUpBounds;
int main() {
    constexpr auto max=(std::numeric_limits<std::uint32_t>::max)();
    static_assert(PrimitiveElements(4,2)==6);
    static_assert(PrimitiveElements(4,max)==0);
    static_assert(PrimitiveElements(3,max)==0);
    static_assert(PrimitiveElements(5,max)==0);
    static_assert(PrimitiveElements(2,max)==0);
    static_assert(PrimitiveElements(1,3)==3);
    static_assert(PrimitiveElements(1,0)==0);
    static_assert(PrimitiveElements(9,3)==0);
    std::uint32_t end=999,local=999;
    assert(DeclaredWindow(0,4,end)&&end==4);
    assert(LocalIndex(3,0,end,local)&&local==3);
    assert(!LocalIndex(4,0,end,local));
    assert(DeclaredWindow(120,8,end)&&end==128);
    assert(LocalIndex(127,120,end,local)&&local==7);
    assert(!LocalIndex(119,120,end,local));
    assert(!LocalIndex(128,120,end,local));
    assert(!DeclaredWindow(max,2,end));
    assert(!DeclaredWindow(0,0,end));
    assert(!DeclaredWindow(262140,8,end));
    assert(DeclaredWindow(262143,1,end)&&end==262144);
}
