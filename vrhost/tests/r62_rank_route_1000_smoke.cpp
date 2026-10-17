// Native 1000 original R62 vs independent R84 eligibility cases.
// The R26_SAFE recovery DLL is not the vehicle-rank quality baseline.
#include "../../src/vr/game/rank_marker_fixedfn_r62.hpp"
#include <iostream>
int main()
{
    int accepted=0,rejected=0;
    for(int i=0;i<1000;++i)
    {
        const int mode=i%10;
        bool owner=true,marker=true,shader=true,triangle=true,rt=true;
        std::uint32_t fvf=0x142u;
        switch(mode)
        {
        case 1: owner=false;break;           // screen HUD
        case 2: marker=false;break;          // stale car anchor
        case 3: shader=false;break;          // normal world VS
        case 4: fvf=0x144u;break;            // other FVF
        case 5: triangle=false;break;        // non indexed quad topology
        case 6: rt=false;break;              // aux target
        case 7: fvf=0x142u+1u;break;         // impostor FVF
        case 8: owner=false;marker=false;break;
        case 9: shader=false;fvf=0x142u+2u;break;
        default:break;
        }
        const bool candidate=OutRunVR::RankMarker::ExactR62FixedFnRankRoute(
            owner,marker,shader,fvf,triangle,rt);
        if(candidate != (mode==0)) return i+1;
        if(candidate)++accepted;else++rejected;
    }
    if(accepted!=100 || rejected!=900) return 1001;
    std::cout<<"PASS R62->R84 exact car-rank FVF142 1000 cases, "
        <<accepted<<" accepted, "<<rejected<<" rejected\n";
    return 0;
}
