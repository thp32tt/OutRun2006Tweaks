#include "runtime/direct_ack_device_epoch.hpp"

int main()
{
    int deviceA = 0, deviceB = 0;
    int contextA = 0, contextB = 0;
    using OutRunVrDirectAckDeviceEpoch::Changed;
    using OutRunVrDirectAckDeviceEpoch::Ready;

    // Stable device/context: keep the pending GPU EVENT and ACK generation.
    if (!Ready(&deviceA, &contextA) ||
        Changed(&deviceA, &contextA, &deviceA, &contextA))
        return 1;
    // Reset/recovery can change either resource independently.
    if (!Changed(&deviceA, &contextA, &deviceB, &contextA) ||
        !Changed(&deviceA, &contextA, &deviceA, &contextB) ||
        !Changed(&deviceA, &contextA, &deviceB, &contextB))
        return 2;
    // A missing device/context never authorizes an old QUERY or publication.
    if (Ready(&deviceA, static_cast<int*>(nullptr)) ||
        Ready(static_cast<int*>(nullptr), &contextA) ||
        Ready(static_cast<int*>(nullptr), static_cast<int*>(nullptr)) ||
        !Changed(&deviceA, &contextA, static_cast<int*>(nullptr), &contextA) ||
        !Changed(&deviceA, &contextA, &deviceA, static_cast<int*>(nullptr)))
        return 3;
    // Rebinding to the same logical pair is idempotent, not a Reset loop.
    if (Changed(&deviceB, &contextB, &deviceB, &contextB) ||
        !Changed(static_cast<int*>(nullptr), static_cast<int*>(nullptr),
            &deviceB, &contextB))
        return 4;
    return 0;
}
