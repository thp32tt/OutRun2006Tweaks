#pragma once
#include <cstdint>
#include <limits>

// Convert a monotonic QPC sample age to milliseconds without overflowing the
// signed 64-bit multiplication. A long-running Windows session with a multi-GHz
// QPC can overflow (now - sample) * 1000 despite an otherwise valid sample.
namespace OutRunVR::Ipc
{
    inline std::int64_t ElapsedQpcMilliseconds(
        std::int64_t sample, std::int64_t now, std::int64_t frequency) noexcept
    {
        if (sample <= 0 || now < sample || frequency <= 0)
            return -1;
        const std::int64_t elapsed = now - sample;
        const std::int64_t wholeSeconds = elapsed / frequency;
        const std::int64_t remainder = elapsed % frequency;
        constexpr std::int64_t limit = (std::numeric_limits<std::int64_t>::max)();
        if (wholeSeconds > limit / 1000)
            return limit;

        // QPC is normally far below this frequency, so keep the common path
        // a single exact integer division.  For extremely high frequencies
        // where remainder*1000 overflows, compute the same floor division by
        // bounded modular addition.  Unlike floating point this preserves the
        // stale/fresh boundary even if long double is only 64-bit on MSVC.
        std::int64_t partial = 0;
        if (remainder <= limit / 1000)
            partial = (remainder * 1000) / frequency;
        else
        {
            const std::int64_t wrapThreshold = frequency - remainder;
            std::int64_t residual = 0;
            for (int step = 0; step < 1000; ++step)
            {
                if (residual >= wrapThreshold)
                {
                    residual -= wrapThreshold;
                    ++partial;
                }
                else
                    residual += remainder; // Sum remains < frequency.
            }
        }
        const std::int64_t base = wholeSeconds * 1000;
        return base > limit - partial ? limit : base + partial;
    }
}
