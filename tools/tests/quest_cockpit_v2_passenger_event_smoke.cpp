#include "../../src/vr/game/quest_cockpit_v2_passenger_event.hpp"
#include <cassert>
using namespace OutRunVR::QuestCockpitV2;
int main() {
    constexpr auto gate=[](bool vr,bool cockpit,bool show,bool hooks,
                            bool start,std::uint32_t id,std::uint32_t fn,
                            bool driver,bool passenger) {
        return ShouldOpenMissingPassenger(vr,cockpit,show,hooks,start,
                                         id,fn,driver,passenger);
    };
    // Byte flags are stored separately from 0x3C-byte sEventWork entries;
    // original 440110 uses BYTE PTR [eventId + 0x79FB48].
    static_assert(OriginalEventFlagsRva==0x39FB48u);
    static_assert(OriginalDriverEventId==0x16au);
    static_assert(OriginalPassengerEventId==0x16bu);
    static_assert(OriginalEventFlagsRva+OriginalPassengerEventId==0x39FCB3u);
    static_assert(!OriginalEventScheduled(0u));
    static_assert(OriginalEventScheduled(OriginalEventPendingInit));
    static_assert(OriginalEventScheduled(OriginalEventInitialized));
    static_assert(!OriginalEventScheduled(0x04u));
    static_assert(OriginalEventSetupAccepted(0x01u));
    static_assert(!OriginalEventSetupAccepted(0x02u));
    static_assert(!OriginalEventSetupAccepted(0x04u));
    static_assert(OriginalPassengerVacant(0));
    static_assert(!OriginalPassengerVacant(0x01u));  // init queued
    static_assert(!OriginalPassengerVacant(0x02u));  // active
    static_assert(!OriginalPassengerVacant(0x04u));  // destroy queued
    static_assert(!OriginalPassengerVacant(0x08u));  // suspended
    static_assert(!OriginalPassengerVacant(0x10u));  // suspended
    static_assert(OriginalPassengerVacant(0x20u));   // unrelated flags
    static_assert(OriginalLicenceSlotRva==0x3C2400u);
    static_assert(OriginalPassengerCharacterIndexValid(0));
    static_assert(OriginalPassengerCharacterIndexValid(5));
    static_assert(!OriginalPassengerCharacterIndexValid(6));
    static_assert(!OriginalPassengerCharacterIndexValid(0xffffffffu));
    static_assert(gate(true,true,true,true,true,0x16c,0x3b,true,false));
    static_assert(!gate(false,true,true,true,true,0x16c,0x3b,true,false));
    static_assert(!gate(true,false,true,true,true,0x16c,0x3b,true,false));
    static_assert(!gate(true,true,false,true,true,0x16c,0x3b,true,false));
    static_assert(!gate(true,true,true,false,true,0x16c,0x3b,true,false));
    static_assert(!gate(true,true,true,true,false,0x16c,0x3b,true,false));
    static_assert(!gate(true,true,true,true,true,0x16b,0x39,true,false));
    static_assert(!gate(true,true,true,true,true,0x16c,0x39,true,false));
    static_assert(!gate(true,true,true,true,true,0x16c,0x3b,false,false));
    static_assert(!gate(true,true,true,true,true,0x16c,0x3b,true,true));
    assert(!gate(true,true,true,true,true,0x16c,0x3b,true,true));
}
