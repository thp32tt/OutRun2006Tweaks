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
// Only a genuinely initialized, non-destroy-pending event may own a
// ROB01/ROB02 model draw.
inline constexpr bool OriginalEventLiveForDisplay(std::uint8_t flags) noexcept {
    return (flags & OriginalEventInitialized)!=0u &&
        (flags & 0x04u)==0u;
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
inline constexpr std::uint32_t OriginalStartAfterPassengerEventId=0x16cu;
inline constexpr std::uint32_t OriginalStartAfterPassengerFunctionId=0x3bu;
// The caller must pass an exact LIVE original ROB02 owner, established
// from 0x79FB48 flag 0x02 plus the 4879B0 callback and work pointer.
// Hide mode affects the original ROB02 draw in either camera, while the
// follow mode admits only a character already present in camera 0.
inline constexpr bool ShouldSuppressOriginalPassenger(
    bool vrEnabled,bool cockpitEnabled,bool followCamera0,
    bool gameplay,bool exactLivePassenger) noexcept {
    return vrEnabled && cockpitEnabled && !followCamera0 &&
        gameplay && exactLivePassenger;
}
}
