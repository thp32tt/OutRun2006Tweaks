#include "../../src/vr/d3d9/stage_extension_eye_plane.hpp"
#include <cmath>
#include <limits>
namespace {
bool Near(float a,float b,float eps=1e-4f) {
    return std::isfinite(a)&&std::isfinite(b)&&std::fabs(a-b)<eps;
}
}
int main() {
    using OutRunVR::StageExtensionPlane::ProjectPixel;
    using OutRunVR::StageExtensionPlane::BuildStageEyePoses;
    const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    float x=0,y=0;
    if(!ProjectPixel(identity,320,240,0,0,640,480,1,x,y) ||
       !Near(x,320)||!Near(y,240))return 1;
    const float left[16]={1,0,0,0,0,1,0,0,0,0,1,0,-0.04f,0,0,1};
    const float right[16]={1,0,0,0,0,1,0,0,0,0,1,0,0.04f,0,0,1};
    float lx=0,ly=0,rx=0,ry=0;
    if(!ProjectPixel(left,320,240,0,0,640,480,1,lx,ly)||
       !ProjectPixel(right,320,240,0,0,640,480,1,rx,ry)||
       !(lx<320&&rx>320&&Near(ly,ry)))return 2;
    float offsets[2][3]{{100.f-0.032f,2,5},{100.f+0.032f,2,5}};
    const float cant=0.12f;
    const float canted[2][4]{{0,-std::sin(cant),0,std::cos(cant)},
                             {0, std::sin(cant),0,std::cos(cant)}};
    float ipd[2][3]{},quats[2][4]{};
    if(!BuildStageEyePoses(offsets,canted,1.f,ipd,quats))return 3;
    if(!Near(ipd[0][0],-0.032f,1e-3f)||
       !Near(ipd[1][0],0.032f,1e-3f)||
       !Near(quats[0][1],-std::sin(cant))||
       !Near(quats[1][1], std::sin(cant)))return 4;
    const float parallel[2][4]{{0,0,0,1},{0,0,0,1}};
    if(!BuildStageEyePoses(offsets,parallel,1.f,ipd,quats)||
       !Near(quats[0][3],1)||!Near(quats[1][3],1))return 5;
    for(auto& eye:ipd)for(float& v:eye)v=17;
    for(auto& eye:quats)for(float& v:eye)v=19;
    const float invalid[2][4]{{0,0,0,1},{0,0,0,0}};
    if(BuildStageEyePoses(offsets,invalid,1.f,ipd,quats)||
       BuildStageEyePoses(offsets,canted,0.f,ipd,quats)||
       BuildStageEyePoses(offsets,canted,
           std::numeric_limits<float>::infinity(),ipd,quats))return 6;
    for(const auto& eye:ipd)for(float v:eye)if(v!=17)return 7;
    for(const auto& eye:quats)for(float v:eye)if(v!=19)return 8;
    offsets[0][0]=std::numeric_limits<float>::quiet_NaN();
    if(BuildStageEyePoses(offsets,canted,1.f,ipd,quats))return 9;
    if(ProjectPixel(identity,0,0,0,0,0,480,1,x,y))return 10;
    const float zero[16]{};
    if(ProjectPixel(zero,320,240,0,0,640,480,1,x,y)||
       ProjectPixel(identity,
          std::numeric_limits<float>::quiet_NaN(),240,
          0,0,640,480,1,x,y)||
       ProjectPixel(identity,320,240,0,0,640,480,-1,x,y))return 11;
    return 0;
}
