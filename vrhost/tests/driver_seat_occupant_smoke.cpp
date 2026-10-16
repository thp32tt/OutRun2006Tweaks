#include "vr/game/driver_seat_occupant.hpp"
using OutRunVR::DriverSeatOccupant::HideVerifiedDriver;
int main()
{
    if (!HideVerifiedDriver(true, 0, 31, 0, -1)) return 1;
    if (HideVerifiedDriver(false, 0, 31, 0, 31)) return 2;
    if (!HideVerifiedDriver(true, 0, 31, 0, 31)) return 3;
    if (HideVerifiedDriver(true, 0, 32, 0, 31)) return 4;
    if (HideVerifiedDriver(true, 1, 31, 0, 31)) return 5;
    if (HideVerifiedDriver(true, 0, 31, -1, -1)) return 6;
    // Native player driver and heroine can have the same robot workId.
    const int driverSet[6] = {10, 20, 30, 40, 50, 60};
    const int heroineSet[6] = {11, 21, 31, 41, 51, 61};
    using OutRunVR::DriverSeatOccupant::HideIdentifiedDriver;
    if (!HideIdentifiedDriver(true, 0, 30, 0, -1,
            driverSet, heroineSet, 6)) return 7;
    if (HideIdentifiedDriver(true, 0, 31, 0, -1,
            driverSet, heroineSet, 6)) return 8;
    if (HideIdentifiedDriver(true, 0, 31, 0, 31,
            driverSet, heroineSet, 6)) return 9;
    if (HideIdentifiedDriver(true, 1, 30, 0, -1,
            driverSet, heroineSet, 6)) return 10;
    if (HideIdentifiedDriver(true, 0, 30, 0, -1,
            nullptr, heroineSet, 6)) return 11;
    if (HideIdentifiedDriver(true, 0, 30, 0, -1,
            driverSet, nullptr, 6)) return 12;
    if (HideIdentifiedDriver(true, 0, 30, 0, -1,
            driverSet, heroineSet, 7)) return 13;
    const int ambiguousHeroine[6] = {11, 21, 30, 41, 51, 61};
    if (HideIdentifiedDriver(true, 0, 30, 0, -1,
            driverSet, ambiguousHeroine, 6)) return 14;
    if (!HideIdentifiedDriver(true, 0, 30, 0, 30,
            driverSet, heroineSet, 6)) return 15;
    if (HideIdentifiedDriver(true, 0, 30, 0, 20,
            driverSet, heroineSet, 6)) return 16;
    if (HideIdentifiedDriver(false, 0, 30, 0, -1,
            driverSet, heroineSet, 6)) return 17;
    return 0;
}
