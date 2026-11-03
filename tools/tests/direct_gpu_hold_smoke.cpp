#include "../../src/vr/d3d9/direct_gpu_hold_policy.hpp"
#include <cassert>
using OutRunVR::DirectGpuHold::PublishPrePresentMono;
static_assert(!PublishPrePresentMono(false,false,false),
              "No fallback when stereo is not requested");
static_assert(PublishPrePresentMono(true,false,false),
              "Classic/SBS fallback retains the original pre-Present marker");
static_assert(!PublishPrePresentMono(true,true,false),
              "Direct GPU handles must not pre-publish mono");
static_assert(!PublishPrePresentMono(true,false,true),
              "Direct-only deferred frame must not clobber the last safe VR frame");
static_assert(!PublishPrePresentMono(true,true,true),
              "Inconsistent direct+hold state must still never publish mono");
int main() {
    for(int stereo=0;stereo<2;++stereo)
        for(int direct=0;direct<2;++direct)
            for(int hold=0;hold<2;++hold)
                assert(PublishPrePresentMono(stereo!=0,direct!=0,hold!=0)==
                       (stereo!=0 && direct==0 && hold==0));
}
