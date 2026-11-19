#include <cassert>
#include <cmath>
#include <iostream>
#include "../src/vr/game/external_car_ground.hpp"
int main() {
    using OutRunVR::DinoSidecar::ComputeExternalFloorLift;
    float applied=-99.f;
    // Measured 2026-11-16 directly from the real delivered 3-car OVC ZIP.
    assert(ComputeExternalFloorLift(0.22f,-0.16723822f,applied));
    assert(std::fabs(applied-0.22f)<0.00001f);
    assert(ComputeExternalFloorLift(0.22f,-0.33408761f,applied));
    assert(std::fabs(applied-0.36908761f)<0.00002f);
    assert(ComputeExternalFloorLift(0.22f,-0.32695001f,applied));
    assert(std::fabs(applied-0.36195001f)<0.00002f);
    assert(ComputeExternalFloorLift(0.5f,-0.33f,applied));
    assert(std::fabs(applied-0.5f)<0.00002f); // user can lift further
    assert(!ComputeExternalFloorLift(0.22f,-1.9f,applied));
    assert(!ComputeExternalFloorLift(0.22f,0.5f,applied));
    assert(!ComputeExternalFloorLift(NAN,-0.33f,applied));
    assert(!ComputeExternalFloorLift(0.22f,NAN,applied));
    assert(!ComputeExternalFloorLift(100.f,-0.33f,applied));
    std::cout<<"OVC_FLOOR_GUARD_PASS F50=0.22 F40=0.369088 288GTO=0.361950\n";
}
