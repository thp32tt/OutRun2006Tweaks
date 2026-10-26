#pragma once
#include <cstdint>

// Exact original GOAL progress E8 / full-graph parent lifetime only.
// Stable queue-chain membership alone is not proof that the producing
// native call was admitted, or that a nested queue pass did not consume it.
namespace OutRunVR::GoalProgress
{
    struct SourceAdmission final
    {
        bool vrAtEntry = false;
        bool goalAtEntry = false;
        bool outsideQueueAtEntry = false;
        std::uint64_t queueEpochAtEntry = 0;

        constexpr bool mayBeginDirect() const noexcept
        {
            return vrAtEntry && goalAtEntry && outsideQueueAtEntry;
        }

        constexpr bool mayPublish(bool vr, bool goal, bool outsideQueue,
                                  std::uint64_t queueEpoch) const noexcept
        {
            return mayBeginDirect() && vr && goal && outsideQueue &&
                queueEpoch == queueEpochAtEntry;
        }
    };

    namespace Regression
    {
        static_assert(SourceAdmission{true,true,true,9}.mayBeginDirect());
        static_assert(SourceAdmission{true,true,true,9}.mayPublish(true,true,true,9));
        static_assert(!SourceAdmission{false,true,true,9}.mayPublish(true,true,true,9));
        static_assert(!SourceAdmission{true,false,true,9}.mayPublish(true,true,true,9));
        static_assert(!SourceAdmission{true,true,false,9}.mayPublish(true,true,true,9));
        static_assert(!SourceAdmission{true,true,true,9}.mayPublish(false,true,true,9));
        static_assert(!SourceAdmission{true,true,true,9}.mayPublish(true,false,true,9));
        static_assert(!SourceAdmission{true,true,true,9}.mayPublish(true,true,false,9));
        static_assert(!SourceAdmission{true,true,true,9}.mayPublish(true,true,true,10));
        // A nested native Flush can increment epoch then return to depth 0.
        constexpr auto PreSourceFlushReenter = [] {
            std::uint64_t epoch = 9;
            SourceAdmission ticket{true,true,true,epoch};
            ++epoch;
            return ticket.mayPublish(true,true,true,epoch);
        };
        // A partial queue pass in original(0x979E0) must not acquire
        // post-CALL ResultProgress ownership retroactively.
        constexpr auto InsideParentQueueReenter = [] {
            std::uint64_t epoch = 9;
            SourceAdmission ticket{true,true,true,epoch};
            const bool admitted = ticket.mayPublish(true,true,true,epoch);
            ++epoch;
            return admitted && ticket.mayPublish(true,true,true,epoch);
        };
        static_assert(!PreSourceFlushReenter());
        static_assert(!InsideParentQueueReenter());
    }
}
