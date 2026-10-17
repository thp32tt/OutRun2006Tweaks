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
    // Each physical Draw* family shares these same exact producer gates.
    // A projected marker with no anchor must NOT gain screen-HUD authority.
    for(int mode=0;mode<12;++mode)
    {
        bool projected=false, anchor=false, hud=false, pause=false;
        bool noShader=true, backbuffer=true, triangle=true;
        std::uint32_t fvf=0x142u;
        switch(mode)
        {
        case 0: projected=true; anchor=true; break;
        case 1: hud=true; break;
        case 2: pause=true; break;
        case 3: projected=true; hud=true; break;  // no anchor: fail closed
        case 4: projected=true; anchor=false; break;
        case 5: break;                           // untagged
        case 6: hud=true; noShader=false; break; // live shader
        case 7: hud=true; fvf=0x144u; break;      // XYZRHW
        case 8: pause=true; backbuffer=false; break;
        case 9: hud=true; triangle=false; break;
        case 10: projected=true; anchor=true; fvf=0x112u; break;
        case 11: projected=true; anchor=true; noShader=false; break;
        }
        const bool expected=mode<=2;
        const bool route=OutRunVR::RankMarker::ExactR84FixedFnSpriteOwner(
            projected,anchor,hud,pause,noShader,fvf,triangle,backbuffer);
        if(route != expected) return 1100+mode;
    }
    std::cout<<"PASS R62->R84 exact car-rank FVF142 1000 cases, "
        <<accepted<<" accepted, "<<rejected<<" rejected\n";
    return 0;
}
