#include "../../src/vr/game/quest_cockpit_v2_phase0_probe.hpp"
#include <cassert>
int main() {
    OutRunVR::QuestCockpitV2::Probe p;
    p.OnCamera(1,false,false); p.OnPlayerCar(1);
    p.OnBegin(10,2);p.OnEnd(true);p.OnBegin(10,2);p.OnEnd(true);
    auto a=p.OnPresent();
    assert(a.ordinal==1&&a.begins==2&&a.ends==2&&!a.poseChanged);
    assert(a.playerCars==1&&a.worldCameras==1&&!a.modeChanged);
    p.OnBegin(11,3);p.OnCamera(26,true,true);
    p.OnBegin(12,3);p.OnPlayerCar(1);p.OnEnd(false);
    auto b=p.OnPresent();
    assert(b.ordinal==2&&b.poseChanged&&b.modeChanged);
    assert(b.borrowedCameras==1&&b.effectCameras==1&&b.failedEnds==1);
    auto c=p.OnPresent();assert(c.ordinal==3&&c.begins==0&&c.playerCars==0);
}
