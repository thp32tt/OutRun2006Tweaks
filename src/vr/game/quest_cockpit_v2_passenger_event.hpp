// Original ROB02 event identity and render-only passenger policy.
// Camera 0 owns the native passenger decision; camera 1 follows that result.
// Never synthesize a missing event or mutate/close native passenger work.
#pragma once
#include <cstdint>
namespace OutRunVR::QuestCockpitV2 {
// Proven in canonical PC OR2006C2C.exe SHA256 68ceb386829066f8...
// 440110 reads/writes BYTE PTR [eventId+0x79FB48]. It does NOT use
// sEventWork::field_0; sEventWork callbacks live at 0x799B30+0x3C*eventId.
inline constexpr std::uintptr_t OriginalEventFlagsRva=0x39fb48u;
inline constexpr std::uint32_t OriginalDriverEventId=0x16au;
// 487F50 selects Licence[slot] from 0x7C2400; the native table has 6
// entries. Its caller must not request a new passenger on an invalid slot.
inline constexpr std::uintptr_t OriginalLicenceSlotRva=0x3c2400u;
inline constexpr bool OriginalPassengerCharacterIndexValid(
    std::uint32_t slot) noexcept {return slot<6u;}
inline constexpr std::uint8_t OriginalEventPendingInit=0x01u;
inline constexpr std::uint8_t OriginalEventInitialized=0x02u;
inline constexpr bool OriginalEventScheduled(std::uint8_t flags) noexcept {
    return (flags & (OriginalEventPendingInit|OriginalEventInitialized))!=0u;
}
// A stale callback pointer and data token remain in sEventWork after close.
// Original game consumers admit an event when (flags & 3) == 2.
// Bit 0 (pending init) and bit 1 (initialized) must NOT both be set:
// the earlier loose bit-1 check accidentally accepted the 0x03 transition.
// Bits 0x08/0x10 can accompany a live 0x02 event (the user's GOAL log
// contains 0x0A and 0x12), so do not reject them as state by themselves.
// A pending destroy (0x04) is never eligible for a forced passenger draw.
inline constexpr bool OriginalEventLiveForDisplay(std::uint8_t flags) noexcept {
    return (flags & (OriginalEventPendingInit|OriginalEventInitialized)) ==
        OriginalEventInitialized && (flags & 0x04u)==0u;
}
inline constexpr bool OriginalEventSetupAccepted(std::uint8_t flags) noexcept {
    return (flags & OriginalEventPendingInit)!=0u;
}
// 440110 preserves the DEST pending bit (0x04). Reopening a closing
// event would lead to destroy+init on the next event-control pass.
// 0x08/0x10 are additional suspended/busy flags; fail closed for all.
inline constexpr bool OriginalPassengerVacant(std::uint8_t flags) noexcept {
    return (flags & 0x1fu)==0u;
}
inline constexpr std::uint32_t OriginalPassengerEventId=0x16bu;
inline constexpr std::uint32_t OriginalPassengerFunctionId=0x39u;
// Canonical PC 514C30 reads EvWorkRobot+4 before any PMT submission:
// bit 0x8000 must be set; if bit 0x08 is set, bit 0x04 must also be set.
// Keep this as a read-only diagnostic predicate until an HMD log proves the
// native actor gate is the remaining cockpit passenger visibility failure.
inline constexpr bool OriginalRobotDisplayGateOpen(
    std::uint32_t workFlags) noexcept {
    return (workFlags&0x8000u)!=0u &&
        !((workFlags&0x08u)!=0u && (workFlags&0x04u)==0u);
}
// Exact physical passenger provenance is narrower than the shared occupant
// LOD0/visibility scope: a user can enable generic OccupantLod0 for driver
// diagnostics too. Keep a recursion-safe depth only around the genuine live
// ROB02 Follow call so 405890 receipts cannot be mislabeled as passenger.
inline thread_local unsigned ExactPassengerRenderDepth=0;
class ScopedExactPassengerRender final {
    bool active_=false;
public:
    explicit ScopedExactPassengerRender(bool exactPassenger) noexcept
        :active_(exactPassenger) {
        if(active_)++ExactPassengerRenderDepth;
    }
    ~ScopedExactPassengerRender() noexcept {
        if(active_ && ExactPassengerRenderDepth!=0)--ExactPassengerRenderDepth;
    }
    ScopedExactPassengerRender(const ScopedExactPassengerRender&)=delete;
    ScopedExactPassengerRender& operator=(const ScopedExactPassengerRender&)=delete;
};
inline bool ExactPassengerRenderActive() noexcept {
    return ExactPassengerRenderDepth!=0;
}
inline constexpr std::uint32_t OriginalStartAfterPassengerEventId=0x16cu;
inline constexpr std::uint32_t OriginalStartAfterPassengerFunctionId=0x3bu;
// The caller must pass an exact LIVE original ROB02 owner, established
// from 0x79FB48 flag 0x02 plus the 4879B0 callback and work pointer.
// "Remove" is cockpit-only. Camera 0 must preserve original ROB02
// rendering regardless of which passenger checkbox is selected.
// The unmodified PC 0x4879B0 driver/passenger display wrapper only
// forwards to 0x487880 when player-car flags[0x4] has 0x4000 selected in
// its 0xC000 mask. In mode 1, this gate often closes while the genuine
// ROB02 event remains initialized and its native callback still executes.
// Restore ONLY this display call for the existing passenger at that gate;
// never fabricate a new event, change simulation car flags, or affect
// third-person/GOAL/driver/NPCs.
inline constexpr bool ShouldBypassPassengerCarDisplayGate(
    bool vrEnabled,bool cockpitEnabled,bool followCamera0,
    bool activeRacingCockpit,bool nativeCameraModeOne,
    bool exactLivePassenger,std::uint32_t nativeCarFlags) noexcept {
    return vrEnabled && cockpitEnabled && followCamera0 &&
        activeRacingCockpit && nativeCameraModeOne && exactLivePassenger &&
        ((nativeCarFlags & 0xc000u)!=0x4000u);
}
// Native original EXE verified: event_display_43FB40 iterates the current
// layer (1 << layer), 0x80 for ROB01/ROB02 (source descriptors 0x16A/B).
// If a LIVE guest's render scene has been masked away while the driver is
// still admitted to the SAME ORIGINAL 0x80 pass, recover the draw only
// after that pass has completed and proved it did not call the ROB02 wrapper.
// Exact synchronous 43FB40 ownership, not OpenXR pose publication, is the
// render-frame admission proof for this native event draw.
// No fallback to another layer, no event creation or persistent scene edit.
inline constexpr std::uint32_t OriginalRobDisplayLayer=0x80u;
inline constexpr bool ShouldRecoverOriginalPassengerScenePass(
    bool vr,bool cockpit,bool follow,bool racing,
    bool modeOne,bool liveOriginalGuest,bool exactNativeScenePass,
    std::uint32_t renderMask,std::int32_t first,std::int32_t last,
    std::uint32_t driverScene,std::uint32_t passengerScene,
    bool driverWrapperReached,bool guestWrapperReached) noexcept {
    return vr && cockpit && follow && racing && modeOne &&
        liveOriginalGuest && exactNativeScenePass &&
        renderMask==OriginalRobDisplayLayer &&
        first<=static_cast<std::int32_t>(OriginalPassengerEventId) &&
        last>=static_cast<std::int32_t>(OriginalPassengerEventId) &&
        (driverScene&renderMask)!=0u &&
        // First allow an entirely disabled passenger layer (native
        // event still live): no other layer could duplicate this draw.
        // Also repair a missed ROB02 wrapper when its original single
        // 0x80 layer is still set AND the original ROB01 wrapper really
        // executed in THIS VERY SAME thread-local event-display pass.
        // Any other layer, including 0x40, 0x100 or a combined mask,
        // remains fail-closed: it may draw elsewhere.
        !guestWrapperReached &&
        (passengerScene==0u ||
         (passengerScene==OriginalRobDisplayLayer &&
          driverWrapperReached));
}
inline constexpr bool ShouldSuppressOriginalPassenger(
    bool vrEnabled,bool cockpitEnabled,bool followCamera0,
    bool activeRacingCockpit,bool nativeCameraModeOne,
    bool exactLivePassenger) noexcept {
    // A GOAL frame is "playable" for other cockpit effects but must never
    // hide the original finish-scene passenger. The caller also excludes
    // scene effects via QuestCockpitV2Active().
    return vrEnabled && cockpitEnabled && !followCamera0 &&
        activeRacingCockpit && nativeCameraModeOne && exactLivePassenger;
}
}
