#include "../../src/vr/game/quest_cockpit_v2_native_frame.hpp"
#include <cassert>
using namespace OutRunVR::QuestCockpitV2;
int main() {
    NativeFrameTracker t;
    t.OnPlayerCallback();
    t.OnFrameEnd();
    auto a=t.OnPresent();
    assert(a.ordinal==1&&a.unownedCallbacks==1&&a.unmatchedEnds==1);
    t.OnFrameEnter(101);
    assert(t.Active()&&t.ActiveEpoch()==101);
    t.OnPlayerCallback();
    t.OnPlayerCar();
    t.OnFrameEnd();
    assert(!t.Active());
    t.OnFrameEnter(102);
    t.OnPlayerCallback();
    t.OnFrameEnd();
    auto b=t.OnPresent();
    assert(b.ordinal==2&&b.enters==2&&b.ends==2);
    assert(b.playerCallbacks==2&&b.playerCars==1);
    assert(b.firstEpoch==101&&b.lastEpoch==102);
    assert(t.OnPresent().enters==0);
    t.OnFrameEnter(103);
    t.OnFrameEnter(104);
    auto c=t.OnPresent();
    assert(c.nestedEntries==1);
    t.OnFrameEnd();
    assert(t.Active());
    t.OnFrameEnd();
    assert(!t.Active());
    t.Clear();
    assert(!t.Active());
    assert(NextVerifiedNativeEpoch()!=0);
}
