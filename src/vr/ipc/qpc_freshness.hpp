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

        // Normal QPC frequencies are far below this bound. Keep ordinary
        // per-Present arithmetic integer-exact; the rare impossible-for-a-PC
        // frequency branch also avoids overflow rather than wrapping stale.
        std::int64_t partial = 0;
        if (remainder <= limit / 1000)
            partial = (remainder * 1000) / frequency;
        else
            partial = static_cast<std::int64_t>(
                (static_cast<long double>(remainder) * 1000.0L) /
                static_cast<long double>(frequency));
        if (partial > 999)
            partial = 999;
        const std::int64_t base = wholeSeconds * 1000;
        return base > limit - partial ? limit : base + partial;
    }
}
