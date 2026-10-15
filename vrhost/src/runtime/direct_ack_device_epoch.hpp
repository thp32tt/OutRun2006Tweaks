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

    // A live DirectGPU copy query and its host-owned SafeEye caches belong
    // to one (device, immediate-context) binding. Reset/recenter may replace
    // the context while retaining the same D3D11 device pointer. Record the
    // new pair before the caller retires old queries and staging resources.
    template <class Device, class Context>
    struct Binding
    {
        Device* device = nullptr;
        Context* context = nullptr;

        constexpr bool Rebind(Device* currentDevice,
            Context* currentContext) noexcept
        {
            if (!Changed(device, context, currentDevice, currentContext))
                return false;
            device = currentDevice;
            context = currentContext;
            return true;
        }
    };

    template <class Device, class Context>
    constexpr bool Ready(Device* device, Context* context) noexcept
    {
        return device != nullptr && context != nullptr;
    }
}
