#pragma once

#include <atomic>
#include <d3d9.h>

namespace OutRunVR::State
{
    // Neutral event fan-out boundary for StateBlock lifecycle notifications.
    // Physical hook ownership is intentionally unchanged in 0002B-A; R31
    // registers its current consumer callbacks here so a later atomic change
    // can move physical hook ownership to R22 without moving cache semantics.
    class StateBlockEvents final
    {
    public:
        using BeginFn = void (*)(IDirect3DDevice9*) noexcept;
        using EndFn = void (*)(IDirect3DDevice9*, HRESULT) noexcept;
        using ApplyFn = void (*)(IDirect3DDevice9*, HRESULT) noexcept;

        static void Configure(BeginFn begin, EndFn end, ApplyFn apply) noexcept
        {
            // Publish terminal callbacks before Begin. Once R22 becomes the
            // single physical owner it may already be dispatching events while
            // R31 registers; a visible Begin must never lack its matching End.
            EndCallback().store(end, std::memory_order_release);
            ApplyCallback().store(apply, std::memory_order_release);
            BeginCallback().store(begin, std::memory_order_release);
        }

        static bool Configured() noexcept
        {
            return BeginCallback().load(std::memory_order_acquire) &&
                EndCallback().load(std::memory_order_acquire) &&
                ApplyCallback().load(std::memory_order_acquire);
        }

        static void Clear() noexcept
        {
            // Stop new Begin notifications first so no new recording interval
            // can start while the matching terminal callbacks are withdrawn.
            BeginCallback().store(nullptr, std::memory_order_release);
            ApplyCallback().store(nullptr, std::memory_order_release);
            EndCallback().store(nullptr, std::memory_order_release);
        }

        static void NotifyBegin(IDirect3DDevice9* device) noexcept
        {
            if (const auto callback =
                    BeginCallback().load(std::memory_order_acquire))
                callback(device);
        }

        static void NotifyEnd(IDirect3DDevice9* device, HRESULT hr) noexcept
        {
            if (const auto callback =
                    EndCallback().load(std::memory_order_acquire))
                callback(device, hr);
        }

        static void NotifyApply(IDirect3DDevice9* device, HRESULT hr) noexcept
        {
            if (const auto callback =
                    ApplyCallback().load(std::memory_order_acquire))
                callback(device, hr);
        }

    private:
        static std::atomic<BeginFn>& BeginCallback() noexcept
        {
            static std::atomic<BeginFn> value{nullptr};
            return value;
        }

        static std::atomic<EndFn>& EndCallback() noexcept
        {
            static std::atomic<EndFn> value{nullptr};
            return value;
        }

        static std::atomic<ApplyFn>& ApplyCallback() noexcept
        {
            static std::atomic<ApplyFn> value{nullptr};
            return value;
        }
    };
}
