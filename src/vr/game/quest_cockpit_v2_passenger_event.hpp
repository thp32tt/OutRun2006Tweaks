// Optional cockpit-only original ROB02 setup. Pure gate deliberately separates
// native start-event admission from guest-memory access and function hooks.
#pragma once
#include <cstdint>
namespace OutRunVR::QuestCockpitV2 {
inline constexpr std::uint32_t OriginalPassengerEventId=0x16bu;
inline constexpr std::uint32_t OriginalPassengerFunctionId=0x39u;
inline constexpr std::uint32_t OriginalStartAfterPassengerEventId=0x16cu;
inline constexpr std::uint32_t OriginalStartAfterPassengerFunctionId=0x3bu;
inline constexpr bool ShouldOpenMissingPassenger(
    bool vrEnabled,bool cockpitEnabled,bool keepPassenger,
    bool originalHooksReady,bool startMode,
    std::uint32_t eventId,std::uint32_t functionId,
    bool driverEventReady,bool passengerEventActive) noexcept {
    return vrEnabled && cockpitEnabled && keepPassenger &&
        originalHooksReady && startMode &&
        eventId==OriginalStartAfterPassengerEventId &&
        functionId==OriginalStartAfterPassengerFunctionId &&
        driverEventReady && !passengerEventActive;
}
}
