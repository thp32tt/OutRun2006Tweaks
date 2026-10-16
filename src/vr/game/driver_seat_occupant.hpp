#pragma once
namespace OutRunVR::DriverSeatOccupant
{
    // Quest has distinct cockpit vehicle and occupant scopes. The PC game
    // must hide only the selected driver and not an unrelated passenger.
    // -1 chrset preserves preexisting WorkId-only INI behavior.
    inline constexpr bool HideVerifiedDriver(bool enabled,
        int robotWorkId, int robotChrset,
        int selectedDriverWorkId, int selectedDriverChrset) noexcept
    {
        return enabled && selectedDriverWorkId >= 0 &&
            robotWorkId == selectedDriverWorkId &&
            (selectedDriverChrset < 0 || robotChrset == selectedDriverChrset);
    }
}
