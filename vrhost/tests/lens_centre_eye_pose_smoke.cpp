#include "vr/d3d9/lens_centre_relative_eye_pose.hpp"
#include <cmath>
#include <limits>
namespace {
bool Near(float a, float b, float epsilon=1.0e-5f)
{
    return std::isfinite(a) && std::isfinite(b) && std::fabs(a-b)<epsilon;
}
}
int main()
{
    float offsets[2][3]{{100.0f-0.032f,2.0f,5.0f},
                        {100.0f+0.032f,2.0f,5.0f}};
    const float cant=0.1f;
    const float eyeQuat[2][4]{
        {0.0f,-std::sin(cant),0.0f,std::cos(cant)},
        {0.0f, std::sin(cant),0.0f,std::cos(cant)}};
    float position[2][3]{},rotation[2][4]{};
    if(!OutRunVR::LensCentre::BuildHeadRelativeEyePose(
            offsets,eyeQuat,position,rotation)) return 1;
    if(!Near(position[0][0],-0.032f,1e-3f) ||
       !Near(position[1][0], 0.032f,1e-3f) ||
       !Near(position[0][1],0.0f) || !Near(position[1][2],0.0f)) return 2;
    // An identity-only eye path would make these two cant values zero.
    if(!Near(rotation[0][1],-std::sin(cant)) ||
       !Near(rotation[1][1], std::sin(cant)) ||
        Near(rotation[0][1],0.0f) || Near(rotation[1][1],0.0f)) return 3;
    const float unnormalized[2][4]{
        {0,-2*std::sin(cant),0,2*std::cos(cant)},
        {0, 2*std::sin(cant),0,2*std::cos(cant)}};
    if(!OutRunVR::LensCentre::BuildHeadRelativeEyePose(
            offsets,unnormalized,position,rotation) ||
       !Near(rotation[1][1],std::sin(cant))) return 4;
    for(auto& eye:position) for(float& x:eye) x=17;
    for(auto& eye:rotation) for(float& x:eye) x=19;
    float invalid[2][4]{{0,0,0,1},{0,0,0,0}};
    if(OutRunVR::LensCentre::BuildHeadRelativeEyePose(
            offsets,invalid,position,rotation)) return 5;
    for(const auto& eye:position) for(float x:eye) if(x!=17) return 6;
    for(const auto& eye:rotation) for(float x:eye) if(x!=19) return 7;
    invalid[1][3]=std::numeric_limits<float>::quiet_NaN();
    if(OutRunVR::LensCentre::BuildHeadRelativeEyePose(
            offsets,invalid,position,rotation)) return 8;
    offsets[0][0]=std::numeric_limits<float>::infinity();
    if(OutRunVR::LensCentre::BuildHeadRelativeEyePose(
            offsets,eyeQuat,position,rotation)) return 9;
    offsets[0][0]=-0.03f;offsets[1][0]=0.03f;
    const float identity[2][4]{{0,0,0,1},{0,0,0,1}};
    if(!OutRunVR::LensCentre::BuildHeadRelativeEyePose(
            offsets,identity,position,rotation) ||
       !Near(rotation[0][3],1) || !Near(rotation[1][3],1)) return 10;
    return 0;
}
