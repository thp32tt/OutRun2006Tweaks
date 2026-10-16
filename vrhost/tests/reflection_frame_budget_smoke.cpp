#include "vr/game/reflection_frame_budget.hpp"
#include <cmath>
#include <limits>
using namespace OutRunVR::ReflectionFrameBudget;
int main()
{
    // Original 60 Hz work distribution and no device-clock dependency.
    auto a=Advance(0.f,.5f,1.f,false,false);
    if(a.faces!=3 || a.pendingFaces!=0.f)return 1;
    // High-refresh 120 Hz: 6 faces each 4 frames at half rate.
    float pending=0.f; int total=0;
    for(int n=0;n<120;++n) {
        const auto r=Advance(pending,.5f,.5f,true,false);
        pending=r.pendingFaces;total+=r.faces;
        if(r.faces>3 || r.faces<0)return 2;
    }
    if(total!=180)return 3;
    // Missed XR frame or long pause: limit to <=2 faces and forget
    // uncapped debt rather than presenting many expensive cube faces.
    a=Advance(99.f,1.f,1000.f,true,true);
    if(a.faces!=2 || a.pendingFaces>1.f)return 4;
    a=Advance(a.pendingFaces,1.f,.5f,true,false);
    if(a.faces>3)return 5;
    a=Advance(0.f,std::numeric_limits<float>::quiet_NaN(),
        .5f,true,false);
    if(a.faces!=0 || !std::isfinite(a.pendingFaces))return 6;
    a=Advance(std::numeric_limits<float>::infinity(),1.f,
        .5f,true,false);
    if(a.faces>3 || !std::isfinite(a.pendingFaces))return 7;
    a=Advance(0.f,1.f,std::numeric_limits<float>::infinity(),
        true,false);
    if(a.faces!=0)return 8;
    // Desktop vanilla mode: no XR frame budget cap.
    a=Advance(0.f,1.f,1.f,false,false);
    if(a.faces!=6)return 9;
    return 0;
}
