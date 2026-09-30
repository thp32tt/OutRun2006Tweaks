#pragma once

#include <atomic>
#include <cstdint>

namespace OutRunVR::State
{
    struct StateBlockSnapshot
    {
        bool reliable = false;
        bool recording = false;
        std::uint64_t recordings = 0;
        std::uint64_t applies = 0;
    };

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

        static bool R31Reliable() noexcept
        {
            return R31ReliableFlag().load(std::memory_order_acquire);
        }

        static bool Reliable() noexcept
        {
            return R22Reliable() && R31Reliable() && !CoverageLost();
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

        static void BeginRecording() noexcept
        {
            Recording() = true;
            ++RecordingGeneration();
        }

        static void EndRecording() noexcept
        {
            Recording() = false;
        }

        static bool IsRecording() noexcept
        {
            return Recording();
        }

        static void NoteApply() noexcept
        {
            ++ApplyGeneration();
        }

        static std::uint64_t RecordingCount() noexcept
        {
            return RecordingGeneration();
        }

        static std::uint64_t ApplyCount() noexcept
        {
            return ApplyGeneration();
        }

        static StateBlockSnapshot Snapshot() noexcept
        {
            StateBlockSnapshot snapshot{};
            snapshot.reliable = Reliable();
            snapshot.recording = IsRecording();
            snapshot.recordings = RecordingCount();
            snapshot.applies = ApplyCount();
            return snapshot;
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

        static bool& Recording() noexcept
        {
            static thread_local bool value = false;
            return value;
        }

        static std::uint64_t& RecordingGeneration() noexcept
        {
            static std::uint64_t value = 0;
            return value;
        }

        static std::uint64_t& ApplyGeneration() noexcept
        {
            static std::uint64_t value = 0;
            return value;
        }
    };
}
