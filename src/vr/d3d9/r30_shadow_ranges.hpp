#pragma once
// Shipped R26+HUD dynamic VB/IB CPU-shadow interval ownership.
// Preserve sorted, coalesced half-open ranges (including adjacent spans).
// No D3D dependency: deterministic host smoke covers the same game routine.
#include <algorithm>
#include <cstdint>
#include <vector>

namespace OutRunVR::R30ShadowRanges
{
    struct ByteRange
    {
        std::uint32_t begin = 0;
        std::uint32_t end = 0;
    };

    inline void Merge(std::vector<ByteRange>& ranges,
        std::uint32_t begin, std::uint32_t end)
    {
        if (begin >= end)
            return;
        // Most dynamic VB/IB writes arrive in ascending order. For the
        // usual append/extend path avoid scanning or shifting old ranges.
        if (!ranges.empty())
        {
            auto& tail = ranges.back();
            if (begin >= tail.begin)
            {
                if (begin <= tail.end)
                    tail.end = (std::max)(tail.end, end);
                else
                    ranges.push_back({ begin, end });
                return;
            }
        }

        // Out-of-order updates: one binary search, one forward union and
        // one contiguous erase. Do not erase an element inside a loop.
        auto first = std::lower_bound(ranges.begin(), ranges.end(), begin,
            [](const ByteRange& range, std::uint32_t point) noexcept {
                return range.end < point;
            });
        if (first == ranges.end() || first->begin > end)
        {
            ranges.insert(first, { begin, end });
            return;
        }
        first->begin = (std::min)(first->begin, begin);
        first->end = (std::max)(first->end, end);
        auto last = first + 1;
        while (last != ranges.end() && last->begin <= first->end)
        {
            first->end = (std::max)(first->end, last->end);
            ++last;
        }
        ranges.erase(first + 1, last);
    }

    inline bool Contains(const std::vector<ByteRange>& ranges,
        std::uint32_t begin, std::uint32_t end) noexcept
    {
        if (begin >= end || ranges.empty())
            return false;
        // Latest streamed tail is a frequent stereo readback.
        if (begin >= ranges.back().begin)
            return end <= ranges.back().end;
        const auto it = std::lower_bound(ranges.begin(), ranges.end(), begin,
            [](const ByteRange& range, std::uint32_t point) noexcept {
                return range.end < point;
            });
        return it != ranges.end() && it->begin <= begin && it->end >= end;
    }
}
