#include "../src/vr/game/driver_seat_yaw_lock.hpp"
#include <cassert>
#include <cmath>
#include <limits>
using OutRunVR::DriverSeatCamera::Vec3;
using OutRunVR::DriverSeatCamera::ComputeVehicleLockedYawLook;
static bool close(float a, float b) {return std::fabs(a-b)<1e-4f;}
int main() {
    Vec3 out{999,999,999}; int sign=0;
    // The native camera is still pointing forward, while the body turned 30deg.
    const Vec3 carForward{0.5f,0.0f,0.8660254f};
    assert(ComputeVehicleLockedYawLook({0,2,0},{0,2,10},carForward,{0,1,0},sign,out));
    assert(sign==1 && close(out.x,5) && close(out.y,2) && close(out.z,8.660254f));
    // Car yaw follows both steering directions without reselecting the sign.
    assert(ComputeVehicleLockedYawLook({0,2,0},{0,2,10},{-0.7071068f,0,0.7071068f},{0,1,0},sign,out));
    assert(close(out.x,-7.071068f) && close(out.z,7.071068f));
    // Pitch and camera position (including a native cockpit offset) are retained.
    assert(ComputeVehicleLockedYawLook({3,2,-4},{3,4,6},{1,0,0},{0,1,0},sign,out));
    assert(close(out.x,13) && close(out.y,4) && close(out.z,-4));
    // Reversed asset Z-basis learns a stable polarity, even when drifting later.
    sign=0;
    assert(ComputeVehicleLockedYawLook({0,0,0},{0,0,10},{0,0,-1},{0,1,0},sign,out));
    assert(sign==-1 && close(out.z,10));
    assert(ComputeVehicleLockedYawLook({0,0,0},{0,0,-10},{0,0,-1},{0,1,0},sign,out));
    assert(close(out.z,10) && sign==-1);
    // A sideways initial view cannot establish a reliable sign.
    sign=0; out={11,12,13};
    assert(!ComputeVehicleLockedYawLook({0,0,0},{10,0,0},{0,0,1},{0,1,0},sign,out));
    assert(sign==0 && out.x==11 && out.y==12 && out.z==13);
    // Singular/invalid poses fail closed, leaving outputs and sign unchanged.
    assert(!ComputeVehicleLockedYawLook({0,0,0},{0,0,0},{0,0,1},{0,1,0},sign,out));
    assert(!ComputeVehicleLockedYawLook({0,0,0},{0,0,10},{0,0,1},{0,0,1},sign,out));
    assert(!ComputeVehicleLockedYawLook({0,0,0},{0,0,10},
        {std::numeric_limits<float>::quiet_NaN(),0,1},{0,1,0},sign,out));
    assert(sign==0 && out.x==11 && out.y==12 && out.z==13);
    return 0;
}
