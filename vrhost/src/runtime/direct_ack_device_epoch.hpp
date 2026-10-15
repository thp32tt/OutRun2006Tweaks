#pragma once

// Host-side D3D11 EVENT/ACK queries are tied to BOTH the device and its
// immediate context. A game Reset can rebind the host without destroying the
// OpenXR session: matching producer frame IDs must never keep old queries.
namespace OutRunVrDirectAckDeviceEpoch
{
    template <class Device, class Context>
    constexpr bool Changed(Device* boundDevice, Context* boundContext,
        Device* currentDevice, Context* currentContext) noexcept
    {
        return boundDevice != currentDevice ||
            boundContext != currentContext;
    }

    template <class Device, class Context>
    constexpr bool Ready(Device* device, Context* context) noexcept
    {
        return device != nullptr && context != nullptr;
    }
}
