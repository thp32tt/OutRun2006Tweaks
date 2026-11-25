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
            // Read-only draws/color-only clear leave the original receipt.
            stamp.OnPotentialWrite(0);
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
        // Model the same-Present stale bootstrap after LEFT writes or a
        // partial clear. RIGHT failure makes replay tempting but not safe.
        for(unsigned cleared: {depth,stencil,depth|stencil}) {
            for(unsigned writes: {0u,depth,stencil,depth|stencil}) {
                for(bool rightFailed: {false,true}) {
                    DepthClearReplayStamp stamp{};
                    stamp.Record(77,cleared);
                    stamp.OnPotentialWrite(writes);
                    const unsigned remaining=cleared&~writes;
                    assert(stamp.flags==remaining);
                    assert(stamp.Current(77)==(remaining!=0));
                    const unsigned replay=rightFailed&&stamp.Current(77)
                        ? stamp.flags:0;
                    assert((replay&writes)==0);
                    assert(replay==(rightFailed?remaining:0));
                    // Old implementation retained cleared even after a write.
                    if(rightFailed&&(cleared&writes)) {
                        const unsigned oldReplay=cleared;
                        assert((oldReplay&writes)!=0);
                        assert(replay!=oldReplay);
                    }
                    stamp.Record(77,cleared); // new successful full clear
                    assert(stamp.Current(77)&&stamp.flags==cleared);
                }
            }
        }
    }
}
