#pragma once

#include <atomic>
#include <cstdint>

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
        static void SetEventConsumerReady(bool reliable) noexcept
        {
            EventConsumerReadyFlag().store(reliable, std::memory_order_release);
        }
        static bool R22Reliable() noexcept
        {
            return R22ReliableFlag().load(std::memory_order_acquire);
        }
        static bool EventConsumerReady() noexcept
        {
            return EventConsumerReadyFlag().load(std::memory_order_acquire);
        }
        static bool Reliable() noexcept
        {
            return R22Reliable() &&
                EventConsumerReady() &&
                !CoverageLost();
        }
        static void SetLifecycleHooksReady(bool ready) noexcept
        {
            LifecycleHooksReadyFlag().store(ready, std::memory_order_release);
        }
        static bool LifecycleHooksReady() noexcept
        {
            return LifecycleHooksReadyFlag().load(std::memory_order_acquire);
        }
        static void MarkCoverageLost() noexcept
        {
            CoverageLostFlag().store(true, std::memory_order_release);
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
        static void NoteRecording() noexcept
        {
            RecordingGenerationCounter().fetch_add(1, std::memory_order_relaxed);
        }
        static void NoteApply() noexcept
        {
            ApplyGenerationCounter().fetch_add(1, std::memory_order_relaxed);
        }
        static std::uint64_t RecordingGeneration() noexcept
        {
            return RecordingGenerationCounter().load(std::memory_order_relaxed);
        }
        static std::uint64_t ApplyGeneration() noexcept
        {
            return ApplyGenerationCounter().load(std::memory_order_relaxed);
        }
        static void SetRecording(bool recording) noexcept
        {
            RecordingFlag() = recording;
        }
        static bool Recording() noexcept
        {
            return RecordingFlag();
        }
    private:
        static std::atomic<bool>& R22ReliableFlag() noexcept
        {
            static std::atomic<bool> value{false};
            return value;
        }
        static std::atomic<bool>& EventConsumerReadyFlag() noexcept
        {
            static std::atomic<bool> value{false};
            return value;
        }
        static std::atomic<bool>& CoverageLostFlag() noexcept
        {
            static std::atomic<bool> value{false};
            return value;
        }
        static std::atomic<bool>& LifecycleHooksReadyFlag() noexcept
        {
            static std::atomic<bool> value{false};
            return value;
        }
        static bool& ResyncPending() noexcept
        {
            static thread_local bool value = false;
            return value;
        }
        static bool& RecordingFlag() noexcept
        {
            static thread_local bool value = false;
            return value;
        }
        static std::atomic<std::uint64_t>& RecordingGenerationCounter() noexcept
        {
            static std::atomic<std::uint64_t> value{0};
            return value;
        }
        static std::atomic<std::uint64_t>& ApplyGenerationCounter() noexcept
        {
            static std::atomic<std::uint64_t> value{0};
            return value;
        }
    };
}
