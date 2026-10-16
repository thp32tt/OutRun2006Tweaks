// Real portable C++ contract of the R84 common rank/rival Calc3D2D
// eye-pose source and XYZRHW eye-delta consumer. Always execute in Release.
#include "vr/d3d9/lens_centre_relative_eye_pose.hpp"
#include "vr/game/projected_rank_stereo.hpp"
#include <cmath>
#include <iostream>
#include <limits>
namespace {
bool Near(float a,float b,float eps=0.0002f) {
    return std::isfinite(a) && std::isfinite(b) && std::fabs(a-b)<eps;
}
bool CheckPoses() {
    using OutRunVR::LensCentre::BuildHeadRelativeEyePose;
    const float offsets[2][3]{{-0.032f,0,0},{0.032f,0,0}};
    const float cant[2][4]{{0,0.10f,0,1},{0,-0.12f,0,1}};
    float ipd[2][3]{}, q[2][4]{};
    if (!BuildHeadRelativeEyePose(offsets,cant,ipd,q) ||
        !Near(ipd[0][0],-0.032f) || !Near(ipd[1][0],0.032f) ||
        !(q[0][1]>0.09f) || !(q[1][1]<-0.11f) ||
        !(2*q[0][1]*q[0][3]>0.18f) ||
        !(2*q[1][1]*q[1][3]<-0.20f)) return false;
    // The historical identity-eye path collapses both canted rays to 0.
    float malformed[2][4]{{0,0.10f,0,1},{0,-0.12f,0,1}};
    malformed[1][2]=std::numeric_limits<float>::quiet_NaN();
    if (BuildHeadRelativeEyePose(offsets,malformed,ipd,q) ||
        !Near(ipd[0][0],-0.032f) || !Near(ipd[1][0],0.032f) ||
        !(q[0][1]>0.09f) || !(q[1][1]<-0.11f)) return false;
    malformed[1][2]=0;
    for (int i=0;i<4;++i) malformed[1][i]=0;
    if (BuildHeadRelativeEyePose(offsets,malformed,ipd,q)) return false;
    const float wrongIPD[2][3]{
        {-0.032f,0,0},{std::numeric_limits<float>::infinity(),0,0}};
    if (BuildHeadRelativeEyePose(wrongIPD,cant,ipd,q)) return false;
    const float parallel[2][4]{{0,0,0,1},{0,0,0,1}};
    return BuildHeadRelativeEyePose(offsets,parallel,ipd,q) &&
        Near(q[0][1],0) && Near(q[1][1],0);
}
bool CheckMovingMarkers() {
    using OutRunVR::RankMarker::StereoNdcShift;
    using OutRunVR::RankMarker::RemapScreenPoint;
    StereoNdcShift s{};
    s.baseX=0.08f;s.baseY=-0.06f;
    s.deltaX[0]=-0.075f;s.deltaX[1]=0.065f;
    s.deltaY[0]=0.01f;s.deltaY[1]=-0.015f;
    for (float width : {640.f,1280.f,3440.f}) {
        float lx=0,ly=0,rx=0,ry=0,mx=0,my=0;
        if (!RemapScreenPoint(width/2,200,0,0,width,480,0.55f,s,0,lx,ly) ||
            !RemapScreenPoint(width/2,200,0,0,width,480,0.55f,s,1,rx,ry) ||
            !(lx<rx) ||
            !RemapScreenPoint(width/2+30,200,0,0,width,480,0.55f,s,0,mx,my) ||
            !Near(mx-lx,16.5f,0.002f) || !Near(my,ly)) return false;
    }
    float x=99,y=77;
    return !RemapScreenPoint(100,100,0,0,0,480,0.55f,s,0,x,y) &&
           !RemapScreenPoint(100,100,0,0,640,480,0.55f,s,2,x,y) &&
           Near(x,99) && Near(y,77);
}
}
int main() {
    if (!CheckPoses() || !CheckMovingMarkers()) {
        std::cerr << "R84 rank marker canted-eye smoke FAIL\n";
        return 1;
    }
    std::cout << "R84 rank marker canted-eye smoke PASS\n";
    return 0;
}
