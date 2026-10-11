#pragma once
#include <cstdint>

// DXGI may wake AcquireNextFrame solely for a mouse-pointer update. That
// event does not change the captured desktop pixels and must not force a
// full-resolution GPU CopyResource. Require the existing cached image,
// an unchanged duplication output, and the absence of a new Present time.
// Every ambiguity (first image, lost/recreated output, actual screen update)
// retains the ordinary capture path.
namespace OutRunVrDesktopCaptureReuse
{
    constexpr bool CanSkipUnchangedPointerFrame(
        bool outputUnchanged, bool haveFrame, bool haveSourceView,
        std::uint32_t accumulatedFrames, std::int64_t lastPresentTime) noexcept
    {
        return outputUnchanged && haveFrame && haveSourceView &&
            accumulatedFrames == 0 && lastPresentTime == 0;
    }

    static_assert(CanSkipUnchangedPointerFrame(true, true, true, 0, 0));
    static_assert(!CanSkipUnchangedPointerFrame(false, true, true, 0, 0));
    static_assert(!CanSkipUnchangedPointerFrame(true, false, true, 0, 0));
    static_assert(!CanSkipUnchangedPointerFrame(true, true, false, 0, 0));
    static_assert(!CanSkipUnchangedPointerFrame(true, true, true, 1, 0));
    static_assert(!CanSkipUnchangedPointerFrame(true, true, true, 0, 123));
}
