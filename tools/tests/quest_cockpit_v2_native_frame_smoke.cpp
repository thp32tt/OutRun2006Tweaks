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
    // Nested native callbacks must restore the PARENT frame epoch.
    t.OnFrameEnter(103);
    t.OnFrameEnter(104);
    auto c=t.OnPresent();
    assert(c.nestedEntries==1 && t.ActiveEpoch()==104);
    t.OnFrameEnd();
    assert(t.Active() && t.ActiveEpoch()==103);
    t.OnPlayerCallback(); // parent event must be attributed to 103
    t.OnFrameEnd();
    assert(!t.Active());

    // Zero/unknown epoch is never a valid cockpit owner.
    t.OnFrameEnter(105);
    t.OnFrameEnter(0);
    assert(!t.Active() && t.ActiveEpoch()==0);
    t.OnPlayerCallback();
    t.OnFrameEnd();
    assert(!t.Active()); // fail closed for the whole parent scope
    t.OnFrameEnd();
    t.OnFrameEnter(106);
    assert(t.ActiveEpoch()==106);
    t.OnFrameEnd();

    // Exceeding the bounded stack must never admit an aliased epoch.
    for(std::uint64_t i=1;i<=33;++i)t.OnFrameEnter(200+i);
    assert(!t.Active() && t.ActiveEpoch()==0);
    t.OnFrameEnd();
    assert(!t.Active()); // overflow child has left; parent still blocked
    for(int i=0;i<31;++i)t.OnFrameEnd();
    assert(!t.Active()); // one original parent remains blocked
    t.OnFrameEnd();
    assert(!t.Active());
    t.OnFrameEnter(301);
    assert(t.ActiveEpoch()==301);
    t.OnFrameEnd();
    assert(t.OnPresent().overflow);
    t.Clear();
    assert(!t.Active());
    assert(NextVerifiedNativeEpoch()!=0);
}
