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

    // Follow Camera 0 = native event/visuals; never create missing ROB02.
    constexpr auto suppress=[](bool vr,bool cockpit,bool follow,
                               bool race,bool passenger) {
        return ShouldSuppressOriginalPassenger(
            vr,cockpit,follow,race,passenger);
    };
    static_assert(!suppress(true,true,true,true,true));
    static_assert(!suppress(true,true,true,true,false)); // no native ROB02
    static_assert(suppress(true,true,false,true,true));  // remove in ANY camera
    static_assert(!suppress(true,true,false,true,false)); // never suppress NPC
    static_assert(!suppress(false,true,false,true,true));
    static_assert(!suppress(true,false,false,true,true));
    static_assert(!suppress(true,true,false,false,true)); // menus unchanged
    assert(suppress(true,true,false,true,true));
}
