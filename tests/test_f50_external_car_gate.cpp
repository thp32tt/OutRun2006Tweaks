#include "src/vr/game/dino_external_sidecar.hpp"
#include <cassert>
#include <cstdio>
int main() {
    using namespace OutRunVR::DinoSidecar;
    Gate g{};
    g.optIn=true;g.vr=true;g.seat=true;g.gameplay=true;g.stereo=true;
    g.playerDraw=true;g.deviceReady=true;g.stateRecording=false;
    g.carKind=0;
    assert(!Eligible(g)); // Default Dino gate MUST reject F50.
    g.expectedCarKind=0;
    assert(Eligible(g)); // Explicit F50 test only.
    g.carKind=1;assert(!Eligible(g));
    g.carKind=0;g.stateRecording=true;assert(!Eligible(g));
    g.stateRecording=false;g.stereo=false;assert(!Eligible(g));
    std::puts("F50_EXPLICIT_SIDE_CAR_VR_GATE_PASS");
    return 0;
}
