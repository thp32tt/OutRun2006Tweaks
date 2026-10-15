#include "../../src/vr/d3d9/stage_extension_eye_plane.hpp"
#include <cassert>
#include <cmath>
#include <limits>

int main()
{
    using OutRunVR::StageExtensionPlane::ProjectPixel;
    const float identity[16] =
        {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    float x = 0, y = 0;
    assert(ProjectPixel(identity,320,240,0,0,640,480,1,x,y));
    assert(x==320 && y==240);
    assert(ProjectPixel(identity,0,0,0,0,640,480,1,x,y));
    assert(x==0 && y==0);
    const float left[16] =
        {1,0,0,0, 0,1,0,0, 0,0,1,0, -0.04f,0,0,1};
    const float right[16] =
        {1,0,0,0, 0,1,0,0, 0,0,1,0, 0.04f,0,0,1};
    float lx=0, ly=0, rx=0, ry=0;
    assert(ProjectPixel(left,320,240,0,0,640,480,1,lx,ly));
    assert(ProjectPixel(right,320,240,0,0,640,480,1,rx,ry));
    assert(lx<320 && rx>320 && ly==ry);
    assert(!ProjectPixel(identity,0,0,0,0,0,480,1,x,y));
    float invalid[16] = {0};
    assert(!ProjectPixel(invalid,320,240,0,0,640,480,1,x,y));
    assert(!ProjectPixel(identity,
        std::numeric_limits<float>::quiet_NaN(),240,
        0,0,640,480,1,x,y));
    assert(!ProjectPixel(identity,320,240,0,0,640,480,-1,x,y));
    return 0;
}
