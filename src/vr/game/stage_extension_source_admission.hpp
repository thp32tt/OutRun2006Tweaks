#pragma once
#include <cstdint>

// One native +TIME E8 source owns both immediate numeric glyphs and queued
// sprani siblings. The lifetime is an exact source CALL, not the entire frame.
// Never publish an optical owner when VR was disabled at entry or when the
// queue/render mode changes while the original game call is executing.
namespace OutRunVR::StageExtension
{
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
    };

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
    }
}
