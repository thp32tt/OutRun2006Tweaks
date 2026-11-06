#include "src/vr/game/dino_external_original_car_gate.hpp"
#include <cassert>
#include <cstdio>
using namespace OutRunVR::DinoSidecar;
int main() {
    // Exact verified Dino, camera=mode1, race, same native frame and XR pose.
    OriginalCarGate g{true,true,true,true,true,true,true,123,123,456,456};
    assert(CanReplaceOriginalCar(g));
    assert(SuppressOriginalCarAfterExternalDraw(g,true));
    // No sidecar, corrupted DDS, shader/stateblock failure, rejected device,
    // or partial Draw must NOT hide the native game car.
    assert(!SuppressOriginalCarAfterExternalDraw(g,false));
    for(unsigned i=0;i<7;++i) {
        OriginalCarGate bad=g;
        switch(i) {
            case 0:bad.optedIn=false;break;
            case 1:bad.ownedPlayer=false;break;
            case 2:bad.gameplay=false;break;
            case 3:bad.cockpitModeOne=false;break;
            case 4:bad.validStereo=false;break;
            case 5:bad.nativeFrameActive=false;break;
            default:bad.deviceReady=false;break;
        }
        assert(!CanReplaceOriginalCar(bad));
        assert(!SuppressOriginalCarAfterExternalDraw(bad,true));
    }
    OriginalCarGate bad=g;
    bad.liveEpoch=124;
    assert(!CanReplaceOriginalCar(bad)); // race/menu frame crossover
    bad=g;bad.livePose=457;
    assert(!CanReplaceOriginalCar(bad)); // new headset pose
    bad=g;bad.ticketEpoch=0;bad.liveEpoch=0;
    assert(!CanReplaceOriginalCar(bad)); // unowned native epoch
    bad=g;bad.ticketPose=0;bad.livePose=0;
    assert(!CanReplaceOriginalCar(bad)); // unowned stereo frame
    bad=g;bad.ticketEpoch=UINT64_MAX;bad.liveEpoch=UINT64_MAX;
    assert(CanReplaceOriginalCar(bad)); // no truncation of 64-bit owner
    std::puts("DINO_EXTERNAL_EXCLUSIVE_ORIGINAL_CAR_FAIL_CLOSED_GATE_PASS");
}
