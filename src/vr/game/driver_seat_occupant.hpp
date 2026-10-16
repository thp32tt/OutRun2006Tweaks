#pragma once
#include <cstddef>
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

    // Original EXE driver and heroine tables contain six character sets each.
    // An occupant workId is not enough to identify the player driver:
    // passenger/heroine objects can share the parent workId.
    inline bool HideIdentifiedDriver(bool enabled, int robotWorkId,
        int robotChrset, int selectedDriverWorkId, int selectedDriverChrset,
        const int* driverChrsets, const int* heroineChrsets,
        std::size_t count) noexcept
    {
        if (!HideVerifiedDriver(enabled, robotWorkId, robotChrset,
                selectedDriverWorkId, selectedDriverChrset) ||
            !driverChrsets || !heroineChrsets || count == 0 || count > 6)
            return false;
        bool isDriver = false;
        bool isHeroine = false;
        for (std::size_t i = 0; i < count; ++i)
        {
            isDriver |= driverChrsets[i] == robotChrset;
            isHeroine |= heroineChrsets[i] == robotChrset;
        }
        // A character appearing in both tables is ambiguous: keep it.
        return isDriver && !isHeroine;
    }
}
