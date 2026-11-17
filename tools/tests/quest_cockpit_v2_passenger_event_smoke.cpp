#include "../../src/vr/game/quest_cockpit_v2_passenger_event.hpp"
#include <cassert>
#include <initializer_list>
using namespace OutRunVR::QuestCockpitV2;
// Exhaustive six-boolean native removal truth table: only 0x3B, i.e.
// VR=1, cockpit=1, follow=0, racing=1, mode1=1, native ROB02=1, hides.
// Every one of the other 63 states (notably camera0 and GOAL) must draw.
constexpr bool PassengerGateTruthTable() {
    for(unsigned bits=0;bits<64u;++bits) {
        const bool actual=ShouldSuppressOriginalPassenger(
            (bits&0x01u)!=0u, (bits&0x02u)!=0u,
            (bits&0x04u)!=0u, (bits&0x08u)!=0u,
            (bits&0x10u)!=0u, (bits&0x20u)!=0u);
        if(actual!=(bits==0x3bu))return false;
    }
    return true;
}
static_assert(PassengerGateTruthTable(),"camera0/GOAL/effect must not hide ROB02");
constexpr bool PassengerDisplayBypassTruthTable() {
    // 64 boolean combinations x 4 distinct original car presentation states.
    for(unsigned bits=0;bits<64u;++bits) {
        for(auto flags:{0x0000u,0x4000u,0x8000u,0xc000u}) {
            const bool actual=ShouldBypassPassengerCarDisplayGate(
                (bits&1u)!=0u,(bits&2u)!=0u,(bits&4u)!=0u,
                (bits&8u)!=0u,(bits&16u)!=0u,(bits&32u)!=0u,flags);
            if(actual!=(bits==63u && flags!=0x4000u))return false;
        }
    }
    return true;
}
static_assert(PassengerDisplayBypassTruthTable(),
    "only existing native ROB02 in active camera-1 follow may bypass the native car flag gate");
static_assert(!ShouldBypassPassengerCarDisplayGate(
    true,true,true,true,false,true,0x8000u),"camera 0 must be untouched");
static_assert(!ShouldBypassPassengerCarDisplayGate(
    true,true,false,true,true,true,0x8000u),"Remove never forces a passenger");
static_assert(!ShouldBypassPassengerCarDisplayGate(
    true,true,true,false,true,true,0x8000u),"GOAL cannot force display");
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
    static_assert(!OriginalEventLiveForDisplay(0x03u)); // pending init + active is NOT native state 2
    static_assert(OriginalEventLiveForDisplay(0x0Au));  // GOAL overlay, low state 2
    static_assert(OriginalEventLiveForDisplay(0x12u));  // transition overlay, low state 2
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
    assert(PassengerDisplayBypassTruthTable());
}
