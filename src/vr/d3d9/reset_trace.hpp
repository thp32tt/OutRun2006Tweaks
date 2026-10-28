#pragma once

#include <atomic>
#include <cstdint>

namespace OutRunVR::D3D9ResetTrace
{
    enum Flags : std::uint32_t
    {
        None = 0,
        ResetSucceeded = 1u << 0,
        PreserveXrPhysical = 1u << 1,
        ClassicReplaySucceeded = 1u << 2,
        BackBufferValid = 1u << 3,
        ViewportValid = 1u << 4,
        ScissorValid = 1u << 5,
    };

    struct Snapshot
    {
        std::uint64_t resetSerial{};
        std::int64_t qpc{};
        std::uint32_t requestedWidth{};
        std::uint32_t requestedHeight{};
        std::uint32_t effectiveWidth{};
        std::uint32_t effectiveHeight{};
        std::uint32_t actualWidth{};
        std::uint32_t actualHeight{};
        std::uint32_t viewportX{};
        std::uint32_t viewportY{};
        std::uint32_t viewportWidth{};
        std::uint32_t viewportHeight{};
        std::int32_t scissorLeft{};
        std::int32_t scissorTop{};
        std::int32_t scissorRight{};
        std::int32_t scissorBottom{};
        std::uint32_t flags{};

        constexpr bool has(Flags flag) const noexcept
        {
            return (flags & static_cast<std::uint32_t>(flag)) != 0;
        }
    };

    // Small lock-free cross-TU diagnostic snapshot. Generation is a seqlock:
    // odd means a Reset publisher is updating fields; even is stable.
    inline std::atomic<std::uint64_t> Generation{0};
    inline std::atomic<std::uint64_t> ResetSerial{0};
    inline std::atomic<std::int64_t> Qpc{0};
    inline std::atomic<std::uint32_t> RequestedWidth{0};
    inline std::atomic<std::uint32_t> RequestedHeight{0};
    inline std::atomic<std::uint32_t> EffectiveWidth{0};
    inline std::atomic<std::uint32_t> EffectiveHeight{0};
    inline std::atomic<std::uint32_t> ActualWidth{0};
    inline std::atomic<std::uint32_t> ActualHeight{0};
    inline std::atomic<std::uint32_t> ViewportX{0};
    inline std::atomic<std::uint32_t> ViewportY{0};
    inline std::atomic<std::uint32_t> ViewportWidth{0};
    inline std::atomic<std::uint32_t> ViewportHeight{0};
    inline std::atomic<std::int32_t> ScissorLeft{0};
    inline std::atomic<std::int32_t> ScissorTop{0};
    inline std::atomic<std::int32_t> ScissorRight{0};
    inline std::atomic<std::int32_t> ScissorBottom{0};
    inline std::atomic<std::uint32_t> SnapshotFlags{0};

    inline std::uint64_t NextResetSerial() noexcept
    {
        return ResetSerial.fetch_add(1, std::memory_order_relaxed) + 1;
    }

    inline void Publish(const Snapshot& snapshot) noexcept
    {
        Generation.fetch_add(1, std::memory_order_acq_rel); // stable -> odd
        ResetSerial.store(snapshot.resetSerial, std::memory_order_relaxed);
        Qpc.store(snapshot.qpc, std::memory_order_relaxed);
        RequestedWidth.store(snapshot.requestedWidth, std::memory_order_relaxed);
        RequestedHeight.store(snapshot.requestedHeight, std::memory_order_relaxed);
        EffectiveWidth.store(snapshot.effectiveWidth, std::memory_order_relaxed);
        EffectiveHeight.store(snapshot.effectiveHeight, std::memory_order_relaxed);
        ActualWidth.store(snapshot.actualWidth, std::memory_order_relaxed);
        ActualHeight.store(snapshot.actualHeight, std::memory_order_relaxed);
        ViewportX.store(snapshot.viewportX, std::memory_order_relaxed);
        ViewportY.store(snapshot.viewportY, std::memory_order_relaxed);
        ViewportWidth.store(snapshot.viewportWidth, std::memory_order_relaxed);
        ViewportHeight.store(snapshot.viewportHeight, std::memory_order_relaxed);
        ScissorLeft.store(snapshot.scissorLeft, std::memory_order_relaxed);
        ScissorTop.store(snapshot.scissorTop, std::memory_order_relaxed);
        ScissorRight.store(snapshot.scissorRight, std::memory_order_relaxed);
        ScissorBottom.store(snapshot.scissorBottom, std::memory_order_relaxed);
        SnapshotFlags.store(snapshot.flags, std::memory_order_relaxed);
        Generation.fetch_add(1, std::memory_order_release); // odd -> stable
    }

    inline Snapshot Read() noexcept
    {
        for (unsigned attempt = 0; attempt < 4; ++attempt)
        {
            const auto before = Generation.load(std::memory_order_acquire);
            if ((before & 1u) != 0)
                continue;

            Snapshot snapshot{};
            snapshot.resetSerial = ResetSerial.load(std::memory_order_relaxed);
            snapshot.qpc = Qpc.load(std::memory_order_relaxed);
            snapshot.requestedWidth = RequestedWidth.load(std::memory_order_relaxed);
            snapshot.requestedHeight = RequestedHeight.load(std::memory_order_relaxed);
            snapshot.effectiveWidth = EffectiveWidth.load(std::memory_order_relaxed);
            snapshot.effectiveHeight = EffectiveHeight.load(std::memory_order_relaxed);
            snapshot.actualWidth = ActualWidth.load(std::memory_order_relaxed);
            snapshot.actualHeight = ActualHeight.load(std::memory_order_relaxed);
            snapshot.viewportX = ViewportX.load(std::memory_order_relaxed);
            snapshot.viewportY = ViewportY.load(std::memory_order_relaxed);
            snapshot.viewportWidth = ViewportWidth.load(std::memory_order_relaxed);
            snapshot.viewportHeight = ViewportHeight.load(std::memory_order_relaxed);
            snapshot.scissorLeft = ScissorLeft.load(std::memory_order_relaxed);
            snapshot.scissorTop = ScissorTop.load(std::memory_order_relaxed);
            snapshot.scissorRight = ScissorRight.load(std::memory_order_relaxed);
            snapshot.scissorBottom = ScissorBottom.load(std::memory_order_relaxed);
            snapshot.flags = SnapshotFlags.load(std::memory_order_relaxed);

            const auto after = Generation.load(std::memory_order_acquire);
            if (before == after && (after & 1u) == 0)
                return snapshot;
        }
        return {};
    }
}
