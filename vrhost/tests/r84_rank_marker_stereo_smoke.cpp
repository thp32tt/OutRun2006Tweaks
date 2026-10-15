// c++ -std=c++17 vrhost/tests/r84_rank_marker_stereo_smoke.cpp -o rank_smoke && ./rank_smoke
#include "../../src/vr/game/projected_rank_stereo.hpp"
#include <cassert>
#include <cmath>
#include <limits>
using OutRunVR::RankMarker::StereoNdcShift;
using OutRunVR::RankMarker::RemapScreenPoint;
static bool eq(float a,float b) { return std::fabs(a-b)<0.001f; }
int main()
{
    StereoNdcShift s{};
    s.baseX=0.25f; s.baseY=-0.2f;
    s.deltaX[0]=-0.06f; s.deltaX[1]=0.06f;
    s.deltaY[0]=0.03f; s.deltaY[1]=-0.03f;
    float lx=0,ly=0,rx=0,ry=0;
    assert(RemapScreenPoint(400,200,0,0,640,480,1,s,0,lx,ly));
    assert(RemapScreenPoint(400,200,0,0,640,480,1,s,1,rx,ry));
    assert(eq(lx,380.8f) && eq(rx,419.2f));
    assert(eq(ly,192.8f) && eq(ry,207.2f));
    float cx=0,cy=0;
    assert(RemapScreenPoint(418,208,0,0,640,480,1,s,0,cx,cy));
    assert(eq(cx-lx,18) && eq(cy-ly,8));
    assert(RemapScreenPoint(400,200,0,0,640,480,0.5f,s,0,cx,cy));
    assert(eq(cx,380.8f));
    assert(!RemapScreenPoint(400,200,0,0,640,480,1,s,2,lx,ly));
    assert(!RemapScreenPoint(400,200,0,0,0,480,1,s,0,lx,ly));
    assert(!RemapScreenPoint(std::numeric_limits<float>::quiet_NaN(),
        200,0,0,640,480,1,s,0,lx,ly));
    s.deltaY[1]=std::numeric_limits<float>::quiet_NaN();
    assert(!RemapScreenPoint(400,200,0,0,640,480,1,s,1,rx,ry));
    assert(RemapScreenPoint(400,200,0,0,640,480,1,s,0,lx,ly));
}
