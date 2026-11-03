#include "../../src/vr/game/quest_cockpit_v2_seat.hpp"
#include <cassert>
#include <cmath>
#include <cstring>
#include <limits>
using namespace OutRunVR::QuestCockpitV2;
static bool near(float a,float b) {return std::fabs(a-b)<1.e-4f;}
int main(){
    std::array<std::uint8_t,30u*36u> table{};
    for(int i=0;i<30;++i){
        const float v[3]{float((i%15)*-0.01f-0.35f),
                         float(0.9f+(i%15)*0.02f),
                         float((i%15)*-0.02f-0.3f)};
        std::memcpy(table.data()+i*36,v,sizeof(v));
    }
    Vec3 a{-99,0,0},b{};
    for(int i=0;i<15;++i){
        assert(OriginalModeOneAnchor(table.data(),table.size(),i,a));
        assert(OriginalModeOneAnchor(table.data(),table.size(),i+15,b));
        assert(near(a.x,b.x)&&near(a.y,b.y)&&near(a.z,b.z));
    }
    assert(!OriginalModeOneAnchor(table.data(),table.size(),-1,a));
    assert(!OriginalModeOneAnchor(table.data(),table.size(),30,a));
    assert(!OriginalModeOneAnchor(table.data(),table.size()-1,0,a));
    assert(!OriginalModeOneAnchor(nullptr,table.size(),0,a));
    Matrix car=Identity;car[12]=10.f;car[13]=20.f;car[14]=30.f;
    SeatPose p{};
    assert(SeatPoseFromCar(car,{-0.35f,0.99f,-0.345f},p));
    assert(near(p.eye.x,9.65f)&&near(p.eye.y,20.99f)&&
           near(p.eye.z,29.655f));
    assert(near(p.look.z,30.655f));
    Matrix rotate=Identity;
    // 90 deg yaw about Y in a D3D row-vector matrix.
    rotate[0]=0;rotate[2]=-1;rotate[8]=1;rotate[10]=0;
    assert(SeatPoseFromCar(rotate,{-0.35f,1.0f,-0.345f},p));
    assert(near(p.eye.x,-0.345f)&&near(p.eye.y,1.f)&&near(p.eye.z,0.35f));
    assert(near(p.look.x,0.655f));
    auto before=p;
    rotate[4]=std::numeric_limits<float>::quiet_NaN();
    assert(!SeatPoseFromCar(rotate,{0,0,0},p));
    assert(near(before.eye.x,p.eye.x));
    SeatPose offset{};
    assert(NativeSeatOffset({0,1,0},{0,1,10},.35f,.18f,0,offset));
    assert(near(offset.eye.z,-.35f)&&near(offset.eye.y,.82f));
    assert(near(offset.look.z,9.65f)&&near(offset.look.y,.82f));
    assert(NativeSeatOffset({3,1,4},{13,1,4},.35f,.18f,.1f,offset));
    assert(near(offset.eye.x,2.65f)&&near(offset.eye.z,3.9f));
    const auto beforeOffset=offset;
    assert(!NativeSeatOffset({0,0,0},{0,0,0},.35f,.18f,0,offset));
    assert(near(offset.eye.x,beforeOffset.eye.x));
    assert(!NativeSeatOffset({0,0,0},{0,0,1},3.f,.18f,0,offset));
    assert(TrialEligible(true,true,true,1,false,true));
    assert(!TrialEligible(true,true,true,2,false,true));
    assert(!TrialEligible(true,true,true,1,true,true));
    assert(!TrialEligible(true,true,true,1,false,false));
}
