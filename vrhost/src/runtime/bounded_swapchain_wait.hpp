#pragma once

// Bound XR_INFINITE_DURATION waits so a wedged runtime/driver cannot leave the
// host process alive forever while the headset shows only black. Finite waits
// requested by callers are preserved exactly. Infinite waits are sliced into
// short waits and returned as XR_TIMEOUT_EXPIRED after the total budget.
// Fallback swapchains keep the already-acquired image and retry its wait on a
// later frame; main compositor callers may still choose to restart the host.
// Never fabricate XR_ERROR_RUNTIME_FAILURE for a runtime that only timed out.

#include <Windows.h>
#include <openxr/openxr.h>

#include <atomic>
#include <cstdint>
#include <iostream>

namespace OutRunVrBoundedSwapchainWait
{
    inline constexpr XrDuration SliceNs = 20'000'000; // 20 ms
    inline constexpr ULONGLONG TotalBudgetMs = 250;
    inline std::atomic<bool> FirstBudgetExceededLogged{ false };

    inline XrResult XRAPI_CALL WaitSwapchainImage(
        XrSwapchain swapchain,
        const XrSwapchainImageWaitInfo* info) noexcept
    {
        if (!info || info->timeout != XR_INFINITE_DURATION)
            return ::xrWaitSwapchainImage(swapchain, info);

        const ULONGLONG start = GetTickCount64();
        for (;;)
        {
            XrSwapchainImageWaitInfo bounded = *info;
            bounded.timeout = SliceNs;
            const XrResult result = ::xrWaitSwapchainImage(swapchain, &bounded);
            if (result != XR_TIMEOUT_EXPIRED)
                return result;

            if (GetTickCount64() - start >= TotalBudgetMs)
            {
                if (!FirstBudgetExceededLogged.exchange(
                        true, std::memory_order_acq_rel))
                {
                    std::cerr
                        << "[R24] xrWaitSwapchainImage exceeded 250ms; returning a recoverable timeout instead of poisoning the swapchain or hanging on black\n";
                }
                return XR_TIMEOUT_EXPIRED;
            }
            SwitchToThread();
        }
    }
}

#define xrWaitSwapchainImage OutRunVrBoundedSwapchainWait::WaitSwapchainImage
