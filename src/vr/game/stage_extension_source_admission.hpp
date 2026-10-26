#pragma once
#include <cstdint>

// One native +TIME E8 source owns both immediate numeric glyphs and queued
// sprani siblings. The lifetime is an exact source CALL, not the entire frame.
// Never publish an optical owner when VR was disabled at entry or when the
// queue/render mode changes while the original game call is executing.
namespace OutRunVR::StageExtension
{
    struct LiveSource final
    {
        bool vr;
        bool outsideQueue;
        std::uint64_t epoch;
    };

    // The installed +TIME entry hook uses this same callback-based gate:
    // a native D3DX flush may reenter the game queue before it returns.
    struct SourceAdmission final
    {
        bool vrAtEntry = false;
        bool outsideQueueAtEntry = false;
        // A native queue can reenter and exit during an exact +TIME CALL.
        std::uint64_t queueEpochAtEntry = 0;

        constexpr bool mayBeginDirect() const noexcept
        {
            return vrAtEntry && outsideQueueAtEntry;
        }

        constexpr bool mayPublish(bool vrAtLeave,
                                  bool outsideQueueAtLeave,
                                  std::uint64_t queueEpochAtLeave = 0) const noexcept
        {
            return mayBeginDirect() && vrAtLeave && outsideQueueAtLeave &&
                queueEpochAtLeave == queueEpochAtEntry;
        }

        template<class Drain, class ReadLive>
        constexpr bool admitAfterDrain(Drain drain, ReadLive readLive) const
        {
            if (!mayBeginDirect())
                return false;
            drain();
            const LiveSource now = readLive();
            return mayPublish(now.vr, now.outsideQueue, now.epoch);
        }
    };

    // Ticket of a previously completed homogeneous batch must survive an
    // unrelated later source's queue epoch. Zero has no direct source proof.
    constexpr bool AllowDirectBatchTicket(
        std::uint64_t batchTicket, std::uint64_t liveTicket,
        bool liveSourceAdmitted) noexcept
    {
        return batchTicket != 0 &&
            (batchTicket != liveTicket || liveSourceAdmitted);
    }

    namespace Regression
    {
        static_assert(SourceAdmission{true, true}.mayBeginDirect());
        static_assert(SourceAdmission{true, true}.mayPublish(true, true));
        static_assert(!SourceAdmission{false, true}.mayBeginDirect());
        static_assert(!SourceAdmission{false, true}.mayPublish(true, true),
            "VR enabled mid-source must not inherit desktop +TIME nodes");
        static_assert(!SourceAdmission{true, false}.mayPublish(true, true),
            "A source entered inside queue draw cannot steal its owner");
        static_assert(!SourceAdmission{true, true}.mayPublish(false, true),
            "VR disabled mid-source must not publish stale HUD tags");
        static_assert(!SourceAdmission{true, true}.mayPublish(true, false),
            "Queue reentry during source exit must keep native ownership");
        static_assert(SourceAdmission{true, true, 9}.mayPublish(true, true, 9));
        static_assert(!SourceAdmission{true, true, 9}.mayPublish(true, true, 10));

        // Entry, pre-entry native Flush callback, and source-exit/physical
        // submission all exercise the same policy used by the real hooks.
        constexpr auto StableDrain = [] {
            std::uint64_t epoch = 9;
            const SourceAdmission source{true, true, epoch};
            return source.admitAfterDrain(
                [&] {}, [&] { return LiveSource{true, true, epoch}; }) &&
                AllowDirectBatchTicket(77, 77,
                    source.mayPublish(true, true, epoch));
        };
        constexpr auto ChangedAtDrain = [] {
            std::uint64_t epoch = 9;
            const SourceAdmission source{true, true, epoch};
            return source.admitAfterDrain(
                [&] { ++epoch; }, // native Flush reentered the queue
                [&] { return LiveSource{true, true, epoch}; });
        };
        constexpr auto ChangedDuringSource = [] {
            std::uint64_t epoch = 9;
            const SourceAdmission source{true, true, epoch};
            const bool admitted = source.admitAfterDrain(
                [&] {}, [&] { return LiveSource{true, true, epoch}; });
            ++epoch; // native +TIME call reentered after admission
            return admitted && AllowDirectBatchTicket(
                77, 77, source.mayPublish(true, true, epoch));
        };
        static_assert(StableDrain());
        static_assert(!ChangedAtDrain());
        static_assert(!ChangedDuringSource());
        static_assert(AllowDirectBatchTicket(76, 77, false),
            "Prior completed delayed batch must keep its proven ownership");
        static_assert(!AllowDirectBatchTicket(77, 77, false));
        static_assert(!AllowDirectBatchTicket(0, 77, true));
    }
}
