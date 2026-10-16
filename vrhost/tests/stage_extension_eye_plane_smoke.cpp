#include "../../src/vr/d3d9/stage_extension_eye_plane.hpp"
#include <cmath>
#include <limits>
#include <initializer_list>
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

    // The original independent-eye GPU route is the reference for full
    // +TIME sprites, numeric glyphs and GOAL 0-99/result quads. The fused
    // source-NDC route must agree at the centre and all viewport edges,
    // including changing desktop size, HUD scale and per-eye cant/skew.
    using OutRunVR::StageExtensionPlane::ProjectPixelPair;
    float matrixL[16]{1,0,0,0.045f, 0,1,0,-0.02f,
                      0,0,1,0, -0.035f,0.01f,0,1};
    float matrixR[16]{1,0,0,-0.03f, 0,1,0,0.015f,
                      0,0,1,0, 0.04f,-0.015f,0,1};
    const float viewports[][2]{{640.f,480.f},{1920.f,1080.f},
                               {3440.f,1440.f},{720.f,1280.f}};
    for (float scale : {0.30f, 0.55f, 1.0f, 1.20f}) {
        for (const auto& dims : viewports) {
            for (float fx : {0.f,0.25f,0.5f,0.75f,1.f}) {
                for (float fy : {0.f,0.3f,0.5f,1.f}) {
                    const float sx=73.f+fx*dims[0], sy=41.f+fy*dims[1];
                    float lrx=0,lry=0,rrx=0,rry=0;
                    float flx=0,fly=0,frx=0,fry=0;
                    if (!ProjectPixel(matrixL,sx,sy,73,41,dims[0],dims[1],
                                      scale,lrx,lry) ||
                        !ProjectPixel(matrixR,sx,sy,73,41,dims[0],dims[1],
                                      scale,rrx,rry) ||
                        !ProjectPixelPair(matrixL,matrixR,sx,sy,73,41,
                                          dims[0],dims[1],scale,
                                          flx,fly,frx,fry) ||
                        !Near(flx,lrx,0.002f) || !Near(fly,lry,0.002f) ||
                        !Near(frx,rrx,0.002f) || !Near(fry,rry,0.002f))
                        return 12;
                }
            }
        }
    }
    // Reject malformed RIGHT-only projection without changing either
    // earlier published eye; also reject invalid screen inputs and scale.
    float badRight[16]{};
    float oldLx=17,oldLy=19,oldRx=23,oldRy=29;
    if (ProjectPixelPair(matrixL,badRight,320,240,0,0,640,480,
                         0.55f,oldLx,oldLy,oldRx,oldRy) ||
        ProjectPixelPair(matrixL,nullptr,320,240,0,0,640,480,
                         0.55f,oldLx,oldLy,oldRx,oldRy) ||
        ProjectPixelPair(matrixL,matrixR,320,240,0,0,0,480,
                         0.55f,oldLx,oldLy,oldRx,oldRy) ||
        ProjectPixelPair(matrixL,matrixR,320,240,0,0,640,480,
                         -1.f,oldLx,oldLy,oldRx,oldRy) ||
        oldLx!=17 || oldLy!=19 || oldRx!=23 || oldRy!=29)
        return 13;
    // R84 paused ESC shell (queued ScreenOverlay2D) and exact option
    // arrows (ScreenHud) share one optical plane but use the independent
    // pause slider/offset. The +TIME/GOAL path supplies zero shift.
    using OutRunVR::StageExtensionPlane::ApplyPostEyeVerticalShiftPair;
    float pauseLeftY=240.f, pauseRightY=250.f;
    if(!ApplyPostEyeVerticalShiftPair(48.f,pauseLeftY,pauseRightY)||
       !Near(pauseLeftY,288.f)||!Near(pauseRightY,298.f))
        return 14;
    // Negative pause offset and independent optical scale also preserve
    // pre-projection bilateral geometry (only post-eye Y is translated).
    if(!ApplyPostEyeVerticalShiftPair(-24.f,pauseLeftY,pauseRightY)||
       !Near(pauseLeftY,264.f)||!Near(pauseRightY,274.f))
        return 15;
    if(!ApplyPostEyeVerticalShiftPair(0.f,pauseLeftY,pauseRightY)||
       !Near(pauseLeftY,264.f)||!Near(pauseRightY,274.f))
        return 16;
    float invalidShiftLeft=11.f, invalidShiftRight=13.f;
    if(ApplyPostEyeVerticalShiftPair(
           std::numeric_limits<float>::infinity(),
           invalidShiftLeft,invalidShiftRight) ||
       invalidShiftLeft!=11.f || invalidShiftRight!=13.f)
        return 17;
    invalidShiftLeft=std::numeric_limits<float>::max();
    invalidShiftRight=13.f;
    if(ApplyPostEyeVerticalShiftPair(
           std::numeric_limits<float>::max(),
           invalidShiftLeft,invalidShiftRight) ||
       invalidShiftLeft!=std::numeric_limits<float>::max() ||
       invalidShiftRight!=13.f)
        return 18;
    // Distinct eye projections retain parallax; pause translation affects
    // only post-eye pixel Y by the same signed viewport fraction.
    float pauseLx=0.f,pauseLy=0.f,pauseRx=0.f,pauseRy=0.f;
    if(!ProjectPixelPair(matrixL,matrixR,320,240,0,0,640,480,
                         0.85f,pauseLx,pauseLy,pauseRx,pauseRy))
        return 19;
    const float originalPauseLy=pauseLy, originalPauseRy=pauseRy;
    if(!ApplyPostEyeVerticalShiftPair(48.f,pauseLy,pauseRy) ||
       !(pauseLx<pauseRx) ||
       !Near(pauseLy,originalPauseLy+48.f,0.002f) ||
       !Near(pauseRy,originalPauseRy+48.f,0.002f))
        return 19;
    return 0;
}
