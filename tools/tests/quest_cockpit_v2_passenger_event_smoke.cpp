#include "../../src/vr/game/quest_cockpit_v2_passenger_event.hpp"
#include <cassert>
using namespace OutRunVR::QuestCockpitV2;
int main() {
    // Original PC: 440110 event byte flags live separately from sEventWork.
    static_assert(OriginalEventFlagsRva==0x39FB48u);
    static_assert(OriginalDriverEventId==0x16au);
    static_assert(OriginalPassengerEventId==0x16bu);
    static_assert(OriginalEventFlagsRva+OriginalPassengerEventId==0x39FCB3u);
    static_assert(!OriginalEventScheduled(0u));
    static_assert(OriginalEventScheduled(OriginalEventPendingInit));
    static_assert(OriginalEventScheduled(OriginalEventInitialized));
    static_assert(!OriginalEventScheduled(0x04u));
    static_assert(!OriginalEventLiveForDisplay(0u));
    static_assert(!OriginalEventLiveForDisplay(0x01u));
    static_assert(OriginalEventLiveForDisplay(0x02u));
    static_assert(!OriginalEventLiveForDisplay(0x04u));
    static_assert(!OriginalEventLiveForDisplay(0x06u));
    static_assert(!OriginalPassengerVacant(0x04u));
    static_assert(OriginalPassengerVacant(0u));

    // Camera 0 always preserves the original ROB02 passenger in BOTH modes.
    constexpr auto suppress=[](bool vr,bool cockpit,bool follow,
                               bool race,bool camera1,bool passenger) {
        return ShouldSuppressOriginalPassenger(
            vr,cockpit,follow,race,camera1,passenger);
    };
    static_assert(!suppress(true,true,true,true,false,true));   // follow, camera0
    static_assert(!suppress(true,true,false,true,false,true));  // remove, camera0
    static_assert(!suppress(true,true,true,true,true,true));    // follow, cockpit
    static_assert(suppress(true,true,false,true,true,true));    // remove, cockpit
    static_assert(!suppress(true,true,false,true,true,false));  // NPCs unaffected
    static_assert(!suppress(false,true,false,true,true,true));  // VR off
    static_assert(!suppress(true,false,false,true,true,true));  // cockpit off
    static_assert(!suppress(true,true,false,false,true,true));  // menu unchanged
    assert(!suppress(true,true,false,true,false,true));
    assert(suppress(true,true,false,true,true,true));
}
