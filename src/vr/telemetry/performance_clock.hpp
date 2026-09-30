#pragma once

#include <Windows.h>
#include <cstdint>

namespace OutRunVR::Telemetry
{
    inline LONGLONG QpcFrequency() noexcept
    {
        static const LONGLONG frequency = []() noexcept {
            LARGE_INTEGER value{};
            return QueryPerformanceFrequency(&value) != FALSE
                ? value.QuadPart : 0;
        }();
        return frequency;
    }

    inline std::uint64_t QpcTicksToUs(std::uint64_t ticks) noexcept
    {
        const LONGLONG frequency = QpcFrequency();
        if (frequency <= 0)
            return 0;
        return static_cast<std::uint64_t>(
            (static_cast<long double>(ticks) * 1000000.0L) /
            static_cast<long double>(frequency));
    }

    inline std::uint64_t ElapsedUs(
        LONGLONG begin, LONGLONG end) noexcept
    {
        const LONGLONG frequency = QpcFrequency();
        if (frequency <= 0 || begin <= 0 || end < begin)
            return 0;
        return static_cast<std::uint64_t>(
            ((end - begin) * 1000000LL) / frequency);
    }
}
