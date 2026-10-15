#pragma once

// Reuse a fresh classic desktop capture for mono recovery within the same XR
// tick; pointer-only notifications and missing pixels always retry normally.
namespace OutRunVrTheaterCaptureReuse
{
    constexpr bool MayReuseCapture(bool attemptedClassicCapture,
                                   bool available, bool freshPixels) noexcept
    {
        return attemptedClassicCapture && available && freshPixels;
    }

    static_assert(MayReuseCapture(true, true, true),
        "Fresh classic desktop pixels can back the recovery theater");
    static_assert(!MayReuseCapture(false, true, true),
        "Do not reuse DirectGPU-only or missing classic captures");
    static_assert(!MayReuseCapture(true, false, true),
        "Unavailable output must use bounded retry");
    static_assert(!MayReuseCapture(true, true, false),
        "Pointer-only and stale frames must use bounded retry");
}
