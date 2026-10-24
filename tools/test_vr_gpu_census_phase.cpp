#include "../src/vr/d3d9/gpu_census_phase.hpp"
#include <cassert>
using OutRunVRStereo::GpuCensusPhase::Legacy;
using OutRunVRStereo::GpuCensusPhase::Dephased;
int main(){
    unsigned seen[64]={};
    for(unsigned frame=0;frame<64;++frame){
        unsigned old=0,modern=0;
        for(unsigned draw=0;draw<64;++draw){
            if(Legacy(frame,draw)){ ++old; assert(frame%16==0 && draw==0); }
            if(Dephased(frame,draw)){ ++modern; ++seen[draw]; }
        }
        assert(old==(frame%16==0 ? 1u : 0u));
        assert(modern==1);
    }
    for(unsigned i=0;i<64;++i) assert(seen[i]==1);
    unsigned sparse=0;
    for(unsigned frame=0;frame<64;++frame)
        for(unsigned i=0;i<16;++i) sparse+=Dephased(frame,i);
    assert(sparse==16);
    return 0;
}
