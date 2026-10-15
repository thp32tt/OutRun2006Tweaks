// Portable runtime regression for the R26+HUD VB/IB valid-shadow intervals.
#include "../../src/vr/d3d9/r30_shadow_ranges.hpp"
#include "../../src/vr/d3d9/r30_shadow_bytes.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>

int main()
{
    using namespace OutRunVR::R30ShadowRanges;
    std::vector<ByteRange> ranges;
    Merge(ranges, 24, 28);
    Merge(ranges, 0, 4);
    Merge(ranges, 12, 16);
    Merge(ranges, 4, 12); // coalesce consecutive, out-of-order writes
    if (ranges.size() != 2 || ranges[0].begin != 0 || ranges[0].end != 16 ||
        Contains(ranges, 15, 17) || !Contains(ranges, 2, 14))
        return 1;
    Merge(ranges, 15, 25); // bridge both intervals once
    if (ranges.size() != 1 || !Contains(ranges, 0, 28))
        return 2;
    Merge(ranges, 20, 20); // empty and inverted writes are not admitted
    Merge(ranges, 30, 29);
    if (ranges.size() != 1 || Contains(ranges, 28, 29))
        return 3;

    // Stress the shipped dynamic-buffer case: 16384 disjoint appends
    // used to require growing linear scans in R26+HUD (quadratic total).
    ranges.clear();
    constexpr std::uint32_t N = 16384;
    for (std::uint32_t i = 0; i < N; ++i)
        Merge(ranges, i * 4, i * 4 + 2);
    if (ranges.size() != N ||
        !Contains(ranges, (N - 1) * 4, (N - 1) * 4 + 2) ||
        Contains(ranges, (N - 1) * 4 + 2, N * 4))
        return 4;
    // One out-of-order bridge must erase all touching intervals in one
    // contiguous operation and preserve the untouched final gap.
    Merge(ranges, 1, N * 4 - 2);
    if (ranges.size() != 1 || ranges[0].begin != 0 ||
        ranges[0].end != N * 4 - 2 ||
        Contains(ranges, N * 4 - 2, N * 4))
        return 5;

    // Differential model: every pixel/byte in a finite shadow buffer is
    // tracked independently, including out-of-order and bridging writes.
    ranges.clear();
    constexpr std::uint32_t Bytes = 8192;
    std::vector<std::uint8_t> known(Bytes, 0);
    std::uint32_t state = 0x1234567u;
    auto next = [&state]() noexcept {
        state ^= state << 13;
        state ^= state >> 17;
        state ^= state << 5;
        return state;
    };
    for (int i = 0; i < 4000; ++i)
    {
        auto begin = next() % Bytes;
        auto end = begin + (next() % 80u);
        if (end > Bytes) end = Bytes;
        Merge(ranges, begin, end);
        for (auto k = begin; k < end; ++k) known[k] = 1;
        if (i % 11 != 0) continue;
        for (int q = 0; q < 150; ++q)
        {
            const auto first = next() % Bytes;
            auto last = first + (next() % 90u);
            if (last > Bytes) last = Bytes;
            bool expected = first < last;
            for (auto k = first; k < last; ++k)
                expected = expected && known[k];
            if (Contains(ranges, first, last) != expected)
                return 6;
        }
        for (std::size_t k = 1; k < ranges.size(); ++k)
            if (ranges[k - 1].end >= ranges[k].begin)
                return 7;
    }
    // DISCARD/new-generation invalidation never inherits prior shadow
    // coverage: the caller clears the same vector on device/lock reset.
    ranges.clear();
    if (Contains(ranges, 0, 16))
        return 8;
    // The actual R26+HUD capture now allocates uninitialized shadow bytes.
    // Reading is permitted ONLY for ranges copied from game Lock/Unlock,
    // including after DISCARD and allocator recovery. Never infer validity
    // from mere allocation or from a previous device generation.
    OutRunVR::R30ShadowBytes::LazyUninitializedBuffer storage;
    constexpr std::uint32_t Allocation = 16u * 1024u * 1024u;
    if (storage.data() || storage.size() != 0)
        return 9;
    storage.resize(Allocation);
    if (!storage.data() || storage.size() != Allocation)
        return 10;
    ranges.clear();
    constexpr std::uint32_t SourceOffset = 4096u;
    const std::uint8_t captured[] = { 0x10u, 0x22u, 0x30u, 0xFFu };
    std::memcpy(storage.data() + SourceOffset, captured, sizeof(captured));
    Merge(ranges, SourceOffset, SourceOffset + sizeof(captured));
    if (!Contains(ranges, SourceOffset, SourceOffset + sizeof(captured)) ||
        Contains(ranges, SourceOffset - 1, SourceOffset + sizeof(captured)) ||
        Contains(ranges, SourceOffset, SourceOffset + sizeof(captured) + 1))
        return 11;
    // Two separated GPU-write observations must retain different payloads
    // with the gap still denied. No unobserved byte's value is inspected.
    constexpr std::uint32_t OtherOffset = SourceOffset + 128u;
    const std::uint8_t other[] = { 0x7Fu, 0x55u, 0x01u };
    std::memcpy(storage.data() + OtherOffset, other, sizeof(other));
    Merge(ranges, OtherOffset, OtherOffset + sizeof(other));
    if (ranges.size() != 2 ||
        !Contains(ranges, OtherOffset, OtherOffset + sizeof(other)) ||
        Contains(ranges, SourceOffset + sizeof(captured), OtherOffset))
        return 16;
    auto* originalAllocation = storage.data();
    storage.resize(Allocation); // same capacity: no reallocation or zero-fill
    if (storage.data() != originalAllocation ||
        std::memcmp(storage.data() + SourceOffset, captured,
                    sizeof(captured)) != 0 ||
        std::memcmp(storage.data() + OtherOffset, other,
                    sizeof(other)) != 0)
        return 12;
    ranges.clear(); // D3DLOCK_DISCARD invalidates previously copied bytes
    if (Contains(ranges, SourceOffset, SourceOffset + sizeof(captured)))
        return 13;
    storage.clear(); // allocation failure / device lifetime invalidation
    if (storage.data() || storage.size() != 0)
        return 14;
    storage.resize(128);
    if (!storage.data() || storage.size() != 128 || !ranges.empty())
        return 15;

    std::cout << "R26+HUD dynamic VB/IB shadow range merge/read PASS\n";
    return 0;
}
