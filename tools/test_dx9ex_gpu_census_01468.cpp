// Portable regression for the optional 01468 RT/PS GPU-census dephase.
// MSVC: cl /nologo /std:c++17 /EHsc /W4 tools\\test_dx9ex_gpu_census_01468.cpp
#include "../src/vr/d3d9/gpu_census_sampling.hpp"
#include <cassert>
#include <cstdint>
namespace P = OutRunVRStereo::GpuCensusSampling;
static_assert(P::StateSample(0,0));
static_assert(P::CensusSample(0,0,false));
static_assert(P::CensusSample(0,0,true));
static_assert(!P::CensusSample(0,1,false));
static_assert(P::CensusSample(57,1,true)); // 57+7=64
static_assert(!P::CensusSample(56,1,true));
int main() {
    unsigned legacyFrames=0,dephasedFrames=0,legacySamples=0,dephasedSamples=0;
    for(std::uint64_t frame=0;frame<32;++frame) {
        unsigned a=0,b=0;
        for(unsigned draw=0;draw<1024;++draw) {
            const bool state=P::StateSample(draw,frame);
            const bool old=P::CensusSample(draw,frame,false);
            const bool corrected=P::CensusSample(draw,frame,true);
            assert(!old || state);
            assert(!corrected || state);
            if(old) ++a;
            if(corrected) ++b;
        }
        if(a) ++legacyFrames;
        if(b) ++dephasedFrames;
        assert(a==(frame%16==0?16u:0u));
        assert(b==16);
        legacySamples+=a;dephasedSamples+=b;
    }
    assert(legacyFrames==2 && legacySamples==32);
    assert(dephasedFrames==32 && dephasedSamples==512);
    for(unsigned frame=0;frame<128;++frame) {
        for(unsigned draw=0;draw<256;++draw) {
            assert(P::CensusSample(draw,frame,true) == (((draw+frame*7u)&63u)==0u));
            assert(P::CensusSample(draw,frame,false) == (((draw&63u)==0u) && (((draw+frame*7u)&15u)==0u)));
        }
    }
    return 0;
}
