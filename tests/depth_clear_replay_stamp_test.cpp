#include <cassert>
#include <initializer_list>
#include "../src/vr/d3d9/depth_clear_replay_stamp.hpp"
using OutRunVR::DepthClearReplayStamp;
int main() {
    constexpr unsigned depth=2, stencil=4;
    for(unsigned slot=0;slot<16;++slot) {
        for(unsigned flags: {depth,stencil,depth|stencil}) {
            DepthClearReplayStamp stamp{};
            assert(!stamp.Current(77));
            stamp.Record(77,flags);
            assert(stamp.Current(77) && stamp.flags==flags);
            stamp.OnBindingChange(false); // same COM identity, redundant SetDepth
            assert(stamp.Current(77) && stamp.flags==flags);
            assert(!stamp.Current(78)); // Present advanced
            stamp.OnBindingChange(true); // same descriptor, different LEFT surface
            assert(!stamp.Current(77) && stamp.flags==0);
            stamp.OnBindingChange(true); // A -> B -> A is not a valid receipt
            assert(!stamp.Current(77));
            stamp.Record(77,flags); // new full clear on currently bound surface
            assert(stamp.Current(77));
            stamp.Invalidate(); // reset or resource retirement, same epoch/address
            assert(!stamp.Current(77) && stamp.flags==0);
            stamp.Record(77,0);
            assert(!stamp.Current(77));
        }
    }
}
