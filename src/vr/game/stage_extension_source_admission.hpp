#pragma once

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

        constexpr bool mayBeginDirect() const noexcept
        {
            return vrAtEntry && outsideQueueAtEntry;
        }

        constexpr bool mayPublish(bool vrAtLeave,
                                  bool outsideQueueAtLeave) const noexcept
        {
            return mayBeginDirect() && vrAtLeave && outsideQueueAtLeave;
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
    }
}
