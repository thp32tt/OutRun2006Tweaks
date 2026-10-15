// Portable runtime regression for the R26+HUD VB/IB valid-shadow intervals.
#include "../../src/vr/d3d9/r30_shadow_ranges.hpp"
#include "../../src/vr/d3d9/r30_shadow_bytes.hpp"
#include "../../src/vr/d3d9/r30_shadow_scratch.hpp"
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

    // Separate shipped stereo READBACK/UP-rebase staging from persistent
    // validity-gated CPU shadow. All requested staging bytes must be written.
    using OutRunVR::R30ScratchBytes::WriteOnlyByteScratch;
    WriteOnlyByteScratch vertexScratch;
    WriteOnlyByteScratch indexScratch;
    vertexScratch.resize(1024);
    if (!vertexScratch.data() || vertexScratch.size() != 1024 ||
        vertexScratch.capacity() < 1024)
        return 17;
    auto* firstScratch = vertexScratch.data();
    std::uint8_t filled[1024]{};
    for (std::size_t k = 0; k < sizeof(filled); ++k)
        filled[k] = static_cast<std::uint8_t>(k & 255u);
    std::memcpy(vertexScratch.data(), filled, sizeof(filled));
    if (std::memcmp(vertexScratch.data(), filled, sizeof(filled)) != 0)
        return 18;
    vertexScratch.resize(16);
    vertexScratch.resize(sizeof(filled));  // varying draw sizes reuse storage
    if (vertexScratch.data() != firstScratch ||
        vertexScratch.size() != sizeof(filled))
        return 19;
    // Reusing storage is NOT reusing payload. Entire next draw is copied
    // again before any vertex transform or per-eye GPU draw.
    std::memset(vertexScratch.data(), 0xA5, vertexScratch.size());
    for (std::size_t k = 0; k < vertexScratch.size(); ++k)
        if (vertexScratch.data()[k] != 0xA5)
            return 20;
    vertexScratch.resize(4096); // growth never requires previous payload
    if (!vertexScratch.data() || vertexScratch.size() != 4096 ||
        vertexScratch.capacity() < 4096)
        return 21;
    std::memset(vertexScratch.data(), 0x42, vertexScratch.size());
    if (vertexScratch.data()[0] != 0x42 ||
        vertexScratch.data()[4095] != 0x42)
        return 22;
    // Both 16-bit and 32-bit IndexedPrimitiveUP paths fill every local
    // index slot; same exact-owned source replays to both eyes.
    for (unsigned bytesPerIndex : {2u, 4u})
    {
        indexScratch.resize(16u * bytesPerIndex);
        for (std::uint32_t k = 0; k < 16; ++k)
        {
            const std::uint32_t local = k + 4u;
            if (bytesPerIndex == 2u)
            {
                const auto shortIndex = static_cast<std::uint16_t>(local);
                std::memcpy(indexScratch.data() + k * bytesPerIndex,
                    &shortIndex, bytesPerIndex);
            }
            else
                std::memcpy(indexScratch.data() + k * bytesPerIndex,
                    &local, bytesPerIndex);
        }
        for (std::uint32_t k = 0; k < 16; ++k)
        {
            std::uint32_t actual = 0;
            if (bytesPerIndex == 2u)
            {
                std::uint16_t shortIndex = 0;
                std::memcpy(&shortIndex, indexScratch.data() +
                    k * bytesPerIndex, bytesPerIndex);
                actual = shortIndex;
            }
            else
                std::memcpy(&actual, indexScratch.data() +
                    k * bytesPerIndex, bytesPerIndex);
            if (actual != k + 4u)
                return 23;
        }
    }
    // Separate full-byte cloned XYZRHW eye staging (not 00873's source
    // shadow scratch). Preserve untouched indexed vertices and attributes.
    WriteOnlyByteScratch leftEye, rightEye;
    constexpr std::size_t Stride = sizeof(float) * 4u + 4u;
    std::uint8_t original[Stride * 3u]{};
    for (std::size_t i = 0; i < sizeof(original); ++i)
        original[i] = static_cast<std::uint8_t>((i * 17u + 3u) & 0xFFu);
    leftEye.resize(sizeof(original));
    rightEye.resize(sizeof(original));
    std::memcpy(leftEye.data(), original, sizeof(original));
    std::memcpy(rightEye.data(), original, sizeof(original));
    if (leftEye.data() == rightEye.data() ||
        std::memcmp(leftEye.data(), original, sizeof(original)) ||
        std::memcmp(rightEye.data(), original, sizeof(original)))
        return 26;
    const float lx = -2.0f, rx = 3.0f;
    std::memcpy(leftEye.data(), &lx, sizeof(lx));
    std::memcpy(rightEye.data(), &rx, sizeof(rx));
    if (std::memcmp(leftEye.data() + Stride, original + Stride, Stride) ||
        std::memcmp(rightEye.data() + Stride, original + Stride, Stride) ||
        std::memcmp(leftEye.data() + 16u, original + 16u, 4u) ||
        std::memcmp(rightEye.data() + 16u, original + 16u, 4u))
        return 27;
    auto* lp = leftEye.data();
    auto* rp = rightEye.data();
    leftEye.resize(Stride);
    rightEye.resize(Stride);
    leftEye.resize(sizeof(original));
    rightEye.resize(sizeof(original));
    if (leftEye.data() != lp || rightEye.data() != rp)
        return 28;
    // Bilateral affine fallback restarts both eye buffers from the immutable
    // original rather than consuming a previous eye's projected result.
    std::memcpy(leftEye.data(), original, sizeof(original));
    std::memcpy(rightEye.data(), original, sizeof(original));
    if (std::memcmp(leftEye.data(), original, sizeof(original)) ||
        std::memcmp(rightEye.data(), original, sizeof(original)))
        return 29;
    leftEye.clear();
    rightEye.clear();
    if (leftEye.data() || rightEye.data() ||
        leftEye.size() || rightEye.size() ||
        leftEye.capacity() || rightEye.capacity())
        return 30;

    vertexScratch.clear();
    indexScratch.clear();
    if (vertexScratch.data() || vertexScratch.size() ||
        vertexScratch.capacity() || indexScratch.data() ||
        indexScratch.size() || indexScratch.capacity())
        return 24;
    // Unobserved gaps remain rejected by the independent validity map;
    // the scratch class never participates in interval admission.
    if (Contains(ranges, 12, 16))
        return 25;

    std::cout << "R26+HUD dynamic VB/IB shadow and stereo scratch PASS\n";
    return 0;
}
