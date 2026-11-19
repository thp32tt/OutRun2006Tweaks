#include "../../src/vr/game/quest_cockpit_v2_turn_yaw.hpp"
#include <cassert>
#include <cmath>
#include <limits>
using OutRunVR::QuestCockpitV2::YawWordDeltaDegrees;
using OutRunVR::QuestCockpitV2::YawRadiansStepDegrees;
using OutRunVR::QuestCockpitV2::BasisZYawRadians;
using OutRunVR::QuestCockpitV2::CameraEyeTargetYawRadians;
int main() {
    assert(YawWordDeltaDegrees(0,0)==0.f);
    assert(std::fabs(YawWordDeltaDegrees(0,65535)-360.f/65536.f)<.001f);
    assert(std::fabs(YawWordDeltaDegrees(65535,0)+360.f/65536.f)<.001f);
    assert(std::fabs(YawWordDeltaDegrees(0x4000,0)-90.f)<.001f);
    assert(std::fabs(YawWordDeltaDegrees(0xc000,0)+90.f)<.001f);
    assert(std::fabs(YawWordDeltaDegrees(0x8000,0)+180.f)<.001f);
    constexpr float pi=3.14159265358979323846f;
    assert(std::fabs(YawRadiansStepDegrees(-pi+.01f,pi-.01f)
                    -.02f*180.f/pi)<.001f);
    assert(std::fabs(YawRadiansStepDegrees(pi-.01f,-pi+.01f)
                    +.02f*180.f/pi)<.001f);
    assert(std::isnan(YawRadiansStepDegrees(
        std::numeric_limits<float>::quiet_NaN(),0.f)));

    // mxRotateY row-3 and exact PC 484DF0 eye-target yaw must agree.
    assert(std::fabs(BasisZYawRadians(0.f,1.f))<.0001f);
    assert(std::fabs(BasisZYawRadians(1.f,0.f)-pi*.5f)<.0001f);
    assert(std::fabs(BasisZYawRadians(-1.f,0.f)+pi*.5f)<.0001f);
    assert(std::fabs(CameraEyeTargetYawRadians(0.f,0.f,0.f,-1.f))<.0001f);
    assert(std::fabs(CameraEyeTargetYawRadians(0.f,0.f,-1.f,0.f)-pi*.5f)<.0001f);
    assert(std::fabs(CameraEyeTargetYawRadians(0.f,0.f,1.f,0.f)+pi*.5f)<.0001f);
    // The old diagnostic used target-eye and was exactly pi out.
    const float oldWrong=std::atan2(0.f-0.f,-1.f-0.f);
    assert(std::fabs(std::fabs(YawRadiansStepDegrees(
        oldWrong,CameraEyeTargetYawRadians(0.f,0.f,0.f,-1.f)))-180.f)<.01f);
    assert(std::isnan(BasisZYawRadians(0.f,0.f)));
    assert(std::isnan(CameraEyeTargetYawRadians(0.f,0.f,0.f,0.f)));
}
