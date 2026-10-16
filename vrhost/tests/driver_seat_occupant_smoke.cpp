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
    return 0;
}
