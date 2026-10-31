#include "../src/vr/d3d11/live_game_blend_extrema.hpp"
#include <cassert>
#include <initializer_list>
using outrun::vr::dx11::live_game_frame::game_native_extremum_admission;
using outrun::vr::dx11::live_game_frame::game_native_extremum_slot;
int main() {
    for (unsigned op : {4u,5u}) {
        for (unsigned mask=1; mask<16; ++mask) {
            if ((mask&7u)==0u) continue;
            for (unsigned variant=0; variant<4; ++variant) {
                const unsigned src=variant==1u||variant==3u?2u:5u;
                const unsigned dst=variant==0u||variant==3u?6u:2u;
                assert(game_native_extremum_admission(op,src,dst,false,mask));
                assert(game_native_extremum_slot(op==5u,variant,mask)<128u);
            }
        }
    }
    assert(!game_native_extremum_admission(5,5,6,true,15));
    assert(!game_native_extremum_admission(4,5,6,false,8));
    assert(!game_native_extremum_admission(3,5,6,false,15));
}
