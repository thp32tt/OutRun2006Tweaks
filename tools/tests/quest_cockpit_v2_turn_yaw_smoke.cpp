#include "../../src/vr/game/quest_cockpit_v2_turn_yaw.hpp"
#include <cassert>
#include <cmath>
#include <limits>
using OutRunVR::QuestCockpitV2::YawWordDeltaDegrees;
using OutRunVR::QuestCockpitV2::YawRadiansStepDegrees;
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
}
