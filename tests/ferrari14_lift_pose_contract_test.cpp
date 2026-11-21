#include <cassert>
#include <cmath>
#include <cstdint>
#include <limits>
#include "../src/vr/game/external_car_ground.hpp"
using namespace OutRunVR::DinoSidecar;
static bool Near(float a,float b) {return std::fabs(a-b)<1e-5f;}
int main() {
    float lift=-9.f;
    // Regression: a real model with a low wheel/local origin needs >1m lift.
    // Previously placement accepted 1.235m, but pose silently reset it to 0.
    assert(ComputeExternalFloorLift(0.f,-1.20f,lift));
    assert(Near(lift,1.235f));
    assert(Near(SanitizeExternalFloorLift(lift),lift));
    assert(ComputeExternalFloorLift(0.f,-1.0f,lift));
    assert(Near(lift,1.035f));
    assert(Near(SanitizeExternalFloorLift(lift),lift));
    // Every permitted model vertical envelope yields an accepted pose lift.
    for (int i=-1200;i<=250;++i) {
        const float minY=static_cast<float>(i)/1000.f;
        for(float requested : {-0.25f,0.f,0.22f,1.0f}) {
            float candidate=-99.f;
            if(!ComputeExternalFloorLift(requested,minY,candidate))continue;
            assert(std::isfinite(candidate));
            assert(candidate<=kMaximumExternalFloorLift);
            assert(Near(SanitizeExternalFloorLift(candidate),candidate));
        }
    }
    // Preserve conservative fail-closed behavior for corrupt callers.
    assert(Near(SanitizeExternalFloorLift(1.25f),1.25f));
    assert(SanitizeExternalFloorLift(1.251f)==0.f);
    assert(SanitizeExternalFloorLift(-0.251f)==0.f);
    assert(SanitizeExternalFloorLift(std::numeric_limits<float>::quiet_NaN())==0.f);
    assert(SanitizeExternalFloorLift(std::numeric_limits<float>::infinity())==0.f);
    // Invalid model bounds must never modify caller's prior result.
    lift=0.123f;
    assert(!ComputeExternalFloorLift(0.f,-1.201f,lift));
    assert(Near(lift,0.123f));
}
