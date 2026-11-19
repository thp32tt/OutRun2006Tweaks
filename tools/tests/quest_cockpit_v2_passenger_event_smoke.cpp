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
// Original source event 362/363 masks = 0x80 (verified from canonical EXE).
// Trigger ONLY a missing passenger mask, not a closed car gate (handled by
// 4879B0), and never on 0/1/2/4/6/8/0x100 layers or out-of-range scans.
constexpr bool PassengerSceneRecoveryTruthTable() {
  for(unsigned bits=0;bits<128u;++bits) {
    const bool native=(bits&1u)!=0u, cockpit=(bits&2u)!=0u;
    const bool follow=(bits&4u)!=0u, race=(bits&8u)!=0u;
    const bool mode=(bits&16u)!=0u, live=(bits&32u)!=0u;
    const bool exactScene=(bits&64u)!=0u;
    constexpr auto guestScene=0u, driverScene=0x80u;
    const bool result=ShouldRecoverOriginalPassengerScenePass(
      native,cockpit,follow,race,mode,live,exactScene,
      0x80u,0,409,driverScene,guestScene,false,false);
    if(result!=(bits==127u))return false;
  }
  return true;
}
static_assert(PassengerSceneRecoveryTruthTable());

static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x40u,0,409,0x40u,0u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,409,0x80u,0x80u,false,false));
// Original 0x80 event remains LIVE but only ROB01 wrapper executes.
static_assert(ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,409,0x80u,0x80u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,409,0x80u,0x80u,true,true));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,409,0x80u,0x80u,false,false));
static_assert(ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,409,0x80u,0u,false,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,409,0x80u,0x180u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,409,0x80u,0x40u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,409,0x80u,0x100u,true,false));
// Remove, camera0, GOAL, non-exact scene and invalid ranges stay fail-closed.
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,false,true,true,true,true,0x80u,0,409,0x80u,0x80u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,false,true,true,0x80u,0,409,0x80u,0x80u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,false,true,true,true,0x80u,0,409,0x80u,0x80u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,false,0x80u,0,409,0x80u,0x80u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,362,0x80u,0x80u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,364,409,0x80u,0x80u,true,false));
static_assert(!ShouldRecoverOriginalPassengerScenePass(
  true,true,true,true,true,true,true,0x80u,0,409,0u,0x80u,true,false));
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
    assert(PassengerSceneRecoveryTruthTable());
}
