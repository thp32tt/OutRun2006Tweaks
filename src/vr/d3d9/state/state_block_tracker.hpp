#pragma once

#include <atomic>

namespace OutRunVR::State
{
    // Phase-2 neutral authority. Physical R22/R31 hooks and their cache
    // invalidation callbacks intentionally remain unchanged until the next
    // atomic hook-ownership migration.
    class StateBlockTracker final
    {
    public:
        static void SetR22Reliable(bool reliable) noexcept
        {
            R22ReliableFlag().store(reliable, std::memory_order_release);
        }
        static void SetR31Reliable(bool reliable) noexcept
        {
            R31ReliableFlag().store(reliable, std::memory_order_release);
        }
        static bool R22Reliable() noexcept
        {
            return R22ReliableFlag().load(std::memory_order_acquire);
        }
        static bool Reliable() noexcept
        {
            return R22Reliable() &&
                R31ReliableFlag().load(std::memory_order_acquire) &&
                !CoverageLost();
        }
        static void MarkCoverageLost() noexcept
        {
            CoverageLostFlag().store(true, std::memory_order_release);
            R31ReliableFlag().store(false, std::memory_order_release);
        }
        static void ResetCoverageLoss() noexcept
        {
            CoverageLostFlag().store(false, std::memory_order_release);
        }
        static bool CoverageLost() noexcept
        {
            return CoverageLostFlag().load(std::memory_order_acquire);
        }
        static void RequireResync() noexcept
        {
            ResyncPending() = true;
        }
        static bool ConsumeResync() noexcept
        {
            bool& pending = ResyncPending();
            if (!pending)
                return false;
            pending = false;
            return true;
        }
    private:
        static std::atomic<bool>& R22ReliableFlag() noexcept
        {
            static std::atomic<bool> value{false};
            return value;
        }
        static std::atomic<bool>& R31ReliableFlag() noexcept
        {
            static std::atomic<bool> value{false};
            return value;
        }
        static std::atomic<bool>& CoverageLostFlag() noexcept
        {
            static std::atomic<bool> value{false};
            return value;
        }
        static bool& ResyncPending() noexcept
        {
            static thread_local bool value = false;
            return value;
        }
    };
}
