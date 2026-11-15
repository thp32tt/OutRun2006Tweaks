#include "src/vr/game/dino_external_sidecar.hpp"
#include <cassert>
#include <iostream>

int main() {
    using namespace OutRunVR::DinoSidecar;
    Gate g{};
    assert(!EligibleForCar(g, 0));
    g.optIn=true; g.vr=true; g.seat=true; g.gameplay=true;
    g.stereo=true; g.playerDraw=true; g.deviceReady=true;
    g.stateRecording=false; g.carKind=0;
    assert(EligibleForCar(g, 0)); // F50, actual PC model ID 0
    assert(!Eligible(g)); // Dino default 1 must not also draw
    g.carKind=1;
    assert(Eligible(g));
    assert(!EligibleForCar(g, 0));
    g.carKind=0;g.stateRecording=true;
    assert(!EligibleForCar(g,0)); // StateBlock recorder blocks test draws
    g.stateRecording=false;g.seat=false;
    assert(!EligibleForCar(g,0)); // Third person/menu not eligible
    std::cout<<"F50_R26_SIDECAR_OPTIN_AND_CARKIND_ISOLATION_PASS\n";
}
