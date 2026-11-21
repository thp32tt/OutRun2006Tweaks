#include "../src/vr/game/external_car_draw_order.hpp"
#include <array>
#include <cassert>
#include <vector>
using OutRunVR::DinoSidecar::MeshInDrawPass;
int main() {
    // Input order deliberately interleaves transparent and opaque meshes.
    const std::array<bool,5> glass{true,false,true,false,true};
    std::vector<unsigned> order;
    for (unsigned pass=0;pass<2u;++pass)
        for (unsigned i=0;i<glass.size();++i)
            if (MeshInDrawPass(glass[i],pass))order.push_back(i);
    assert((order==std::vector<unsigned>{1,3,0,2,4}));
    // Every mesh is submitted exactly once, never outside the two passes.
    for (unsigned i=0;i<glass.size();++i) {
        assert(MeshInDrawPass(glass[i],0u) != MeshInDrawPass(glass[i],1u));
        assert(!MeshInDrawPass(glass[i],2u));
    }
    // All-opaque and all-glass OVCs do not produce spurious extra draws.
    for (bool isGlass:{false,true}) {
        unsigned count=0;
        for(unsigned pass=0;pass<2u;++pass)
            for(unsigned mesh=0;mesh<78u;++mesh)
                if(MeshInDrawPass(isGlass,pass))++count;
        assert(count==78u);
    }
}
