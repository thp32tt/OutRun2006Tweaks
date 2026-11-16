#include "../src/vr/game/dino_external_sidecar.hpp"
#include <cassert>

using OutRunVR::DinoSidecar::Eligible;
using OutRunVR::DinoSidecar::Gate;

static Gate Base() {
    Gate g{};
    g.optIn=true;
    g.vr=true;
    g.seat=true;
    g.gameplay=true;
    g.stereo=true;
    g.playerDraw=true;
    g.deviceReady=true;
    g.stateRecording=false;
    return g;
}

int main() {
    {
        auto g=Base();
        g.allowOtherFerrari=false;
        g.carKind=0;
        g.carId=255;
        assert(Eligible(g));
    }
    for(unsigned id: {0u,1u,6u,7u,11u,22u,26u,29u}) {
        auto g=Base();
        g.allowOtherFerrari=true;
        g.carKind=9;
        g.carId=static_cast<unsigned char>(id);
        g.expectedCarId=static_cast<unsigned char>(id);
        assert(Eligible(g));
    }
    for(unsigned id: {30u,31u,254u,255u}) {
        auto g=Base();
        g.allowOtherFerrari=true;
        g.carKind=0;
        g.carId=static_cast<unsigned char>(id);
        g.expectedCarId=static_cast<unsigned char>(id);
        assert(!Eligible(g));
    }
    {
        auto g=Base();
        g.allowOtherFerrari=true;
        g.carId=12;
        g.expectedCarId=13;
        assert(!Eligible(g));
    }
    {
        auto g=Base();
        g.allowOtherFerrari=true;
        g.carId=12;
        g.expectedCarId=12;
        g.stateRecording=true;
        assert(!Eligible(g));
    }
    return 0;
}
