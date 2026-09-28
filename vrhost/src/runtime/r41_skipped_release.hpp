#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <utility>

namespace OutRunVrR41SkippedRelease
{
    struct Identity
    {
        std::uint32_t clientPid = 0;
        std::uint32_t runGeneration = 0;
        std::uint32_t transportGeneration = 0;
        std::uint32_t slot = 0;
        std::uint32_t frameId = 0;
    };

    constexpr bool Valid(const Identity& value, std::size_t slotCount) noexcept
    {
        return value.clientPid != 0 &&
            value.runGeneration != 0 &&
            value.transportGeneration != 0 &&
            value.frameId != 0 &&
            value.slot < slotCount;
    }

    constexpr bool SameProducer(
        const Identity& a, const Identity& b) noexcept
    {
        return a.clientPid == b.clientPid &&
            a.runGeneration == b.runGeneration &&
            a.transportGeneration == b.transportGeneration;
    }

    constexpr bool SameIdentity(
        const Identity& a, const Identity& b) noexcept
    {
        return SameProducer(a, b) &&
            a.slot == b.slot &&
            a.frameId == b.frameId;
    }

    enum class StageResult : std::uint8_t
    {
        Invalid = 0,
        Staged,
        AlreadyPending,
        ReplacedStaleProducer,
        LiveSlotConflict,
    };

    // Pure LEVEL0 owner for DirectGPU frames that were never sampled by D3D11.
    // Unlike sampled frames, these do not need a GPU EVENT; they only need a
    // durable retry if publishing the per-slot completion ACK temporarily fails.
    //
    // One entry per ring slot is intentional. Seeing a different frame for the
    // same live producer identity before the old release was acknowledged is a
    // contract violation and must fail closed rather than silently replacing it.
    template <std::size_t SlotCount>
    class Queue
    {
    public:
        struct Entry
        {
            bool pending = false;
            Identity identity{};
        };

        StageResult Stage(const Identity& identity) noexcept
        {
            if (!Valid(identity, SlotCount))
                return StageResult::Invalid;

            Entry& entry = entries_[identity.slot];
            if (!entry.pending)
            {
                entry.pending = true;
                entry.identity = identity;
                return StageResult::Staged;
            }

            if (SameIdentity(entry.identity, identity))
                return StageResult::AlreadyPending;

            if (SameProducer(entry.identity, identity))
                return StageResult::LiveSlotConflict;

            // A producer run/generation change means the old mapping can no
            // longer be written safely. Drop that stale retry owner and retain
            // the new producer identity for the same physical ring slot.
            entry.identity = identity;
            return StageResult::ReplacedStaleProducer;
        }

        template <typename IsCurrentProducer, typename Publish>
        void Retry(
            IsCurrentProducer&& isCurrentProducer,
            Publish&& publish) noexcept
        {
            for (Entry& entry : entries_)
            {
                if (!entry.pending)
                    continue;

                if (!std::forward<IsCurrentProducer>(
                        isCurrentProducer)(entry.identity))
                {
                    entry = {};
                    continue;
                }

                if (std::forward<Publish>(publish)(entry.identity))
                    entry = {};
            }
        }

        bool Pending(const Identity& identity) const noexcept
        {
            return Valid(identity, SlotCount) &&
                entries_[identity.slot].pending &&
                SameIdentity(entries_[identity.slot].identity, identity);
        }

        bool SlotBlocked(
            const Identity& producerIdentity) const noexcept
        {
            if (!Valid(producerIdentity, SlotCount))
                return false;
            const Entry& entry = entries_[producerIdentity.slot];
            return entry.pending &&
                SameProducer(entry.identity, producerIdentity);
        }

        std::size_t PendingCount() const noexcept
        {
            std::size_t count = 0;
            for (const Entry& entry : entries_)
                if (entry.pending)
                    ++count;
            return count;
        }

        const Entry& At(std::size_t slot) const noexcept
        {
            return entries_[slot];
        }

    private:
        std::array<Entry, SlotCount> entries_{};
    };
}
