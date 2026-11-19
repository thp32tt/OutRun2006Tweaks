#pragma once

#include <atomic>

namespace OutRunVR::GameResetEvents
{
    using BeforeResetFn = void (*)() noexcept;

    inline std::atomic<BeforeResetFn>& Callback() noexcept
    {
        static std::atomic<BeforeResetFn> value{nullptr};
        return value;
    }

    inline void Configure(BeforeResetFn callback) noexcept
    {
        Callback().store(callback, std::memory_order_release);
    }

    inline void Clear() noexcept
    {
        Callback().store(nullptr, std::memory_order_release);
    }

    inline void NotifyBeforeReset() noexcept
    {
        if (const auto callback = Callback().load(std::memory_order_acquire))
            callback();
    }
}
