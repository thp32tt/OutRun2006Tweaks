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
    // Full-frame projected CABE flare discs share this exact widened
    // eye-centre conversion. The old float sum overflowed even when each
    // OpenXR eye origin was finite, losing the entire binocular effect.
    const float largest = (std::numeric_limits<float>::max)();
    const float largeOffsets[2][3]{
        {largest, largest, largest}, {largest, largest, largest}};
    float projectedRelative[2][3]{
        {17.f,17.f,17.f}, {19.f,19.f,19.f}};
    if(!OutRunVR::LensCentre::BuildHeadRelativeEyeOffsets(
           largeOffsets,projectedRelative)) return 11;
    for(const auto& eye:projectedRelative)
        for(float v:eye) if(!Near(v,0.f)) return 12;
    // One corrupt eye must leave both previous eyes unchanged, never
    // partially publish a transform or inherit a previous stereo origin.
    const float invalidOffsets[2][3]{
        {0.f,0.f,0.f},
        {std::numeric_limits<float>::quiet_NaN(),0.f,0.f}};
    if(OutRunVR::LensCentre::BuildHeadRelativeEyeOffsets(
           invalidOffsets,projectedRelative)) return 13;
    for(const auto& eye:projectedRelative)
        for(float v:eye) if(!Near(v,0.f)) return 14;
    // The R84 CPU-projected smoke/skid/world-effects path reuses this
    // shared bilateral origin helper for both full-world and affine eyes.
    const float worldEffectsEyes[2][3]{
        {1024.f-0.03125f,4096.f-0.125f,-2048.f-0.0625f},
        {1024.f+0.03125f,4096.f+0.125f,-2048.f+0.0625f}};
    float worldEffectsRelative[2][3]{{71,72,73},{74,75,76}};
    if(!OutRunVR::LensCentre::BuildHeadRelativeEyeOffsets(
           worldEffectsEyes,worldEffectsRelative)) return 15;
    for(int axis=0; axis<3; ++axis)
        if(!Near(worldEffectsRelative[0][axis],
                 -worldEffectsRelative[1][axis])) return 16;
    if(!Near(worldEffectsRelative[0][0],-0.03125f) ||
       !Near(worldEffectsRelative[1][1],0.125f) ||
       !Near(worldEffectsRelative[0][2],-0.0625f)) return 17;
    // The same production helper rejects a corrupt right eye atomically;
    // neither world-effect eye can inherit the last frame's valid IPD.
    float malformedWorldEffects[2][3]{
        {0.f,0.f,0.f}, {0.f,0.f,
        std::numeric_limits<float>::infinity()}};
    if(OutRunVR::LensCentre::BuildHeadRelativeEyeOffsets(
           malformedWorldEffects,worldEffectsRelative)) return 18;
    if(!Near(worldEffectsRelative[0][0],-0.03125f) ||
       !Near(worldEffectsRelative[1][1],0.125f)) return 19;
    return 0;
}
