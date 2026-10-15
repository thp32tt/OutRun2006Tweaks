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

    // Exercise the exact binding object used by R32 SafeEye/fence recovery,
    // not merely the stateless comparator. Equal device + changed context
    // MUST retire the previous DirectGPU pair before a cached frame is reused.
    OutRunVrDirectAckDeviceEpoch::Binding<int, int> binding{};
    unsigned invalidations = 0;
    const auto adopt = [&](int* device, int* context)
    {
        if (binding.Rebind(device, context))
            ++invalidations; // models R32ResetDirectCaches/ResetSafeEyes/fence
    };
    adopt(&deviceA, &contextA);
    adopt(&deviceA, &contextA);
    if (invalidations != 1 || binding.device != &deviceA ||
        binding.context != &contextA)
        return 5;
    adopt(&deviceA, &contextB); // same device, new immediate context
    if (invalidations != 2 || binding.device != &deviceA ||
        binding.context != &contextB)
        return 6;
    adopt(&deviceB, &contextB); // new device, same context
    if (invalidations != 3 || binding.device != &deviceB ||
        binding.context != &contextB)
        return 7;
    adopt(nullptr, nullptr); // device loss must retire the last valid pair
    adopt(nullptr, nullptr);
    if (invalidations != 4 || binding.device || binding.context)
        return 8;
    adopt(&deviceB, &contextA); // recovery must republish once
    adopt(&deviceB, &contextA);
    if (invalidations != 5 || binding.device != &deviceB ||
        binding.context != &contextA)
        return 9;
    return 0;
}
