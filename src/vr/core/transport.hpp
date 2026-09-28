#pragma once

#include "vr/core/frame_types.hpp"

#include <cstdint>

namespace OutRunVR::Core
{
    struct AdapterId
    {
        std::uint32_t luidLow{};
        std::int32_t luidHigh{};

        friend constexpr bool operator==(const AdapterId&, const AdapterId&) = default;
    };

    enum class TransportKind : std::uint32_t
    {
        None = 0,
        D3D9ExShared = 1,
        DesktopDuplication = 2,
        Dxvk = 3,
        NativeD3D11 = 4,
    };

    // Backend-neutral publication descriptor. Cross-process transports must
    // carry both process identities plus run/transport generations so a stale
    // slot from a previous game or host lifetime can never be acknowledged.
    struct FrameSlot
    {
        std::uint32_t producerPid{};
        std::uint32_t consumerPid{};
        std::uint32_t runGeneration{};
        std::uint32_t generation{};
        std::uint32_t slot{};
        std::uint64_t frameId{};
        std::uintptr_t leftHandle{};
        std::uintptr_t rightHandle{};
        std::uint32_t width{};
        std::uint32_t height{};
        std::uint32_t format{};
    };

    // Consumer completion is per-slot and identity-bound. A global frame ACK is
    // insufficient because a surviving mapping can otherwise release textures
    // owned by a different producer run or transport generation.
    struct FrameAck
    {
        std::uint32_t consumerPid{};
        std::uint32_t producerPid{};
        std::uint32_t runGeneration{};
        std::uint32_t generation{};
        std::uint32_t slot{};
        std::uint64_t completedFrameId{};
    };

    [[nodiscard]] constexpr bool FrameSlotIdentityValid(
        const FrameSlot& value) noexcept
    {
        return value.producerPid != 0 &&
            value.consumerPid != 0 &&
            value.runGeneration != 0 &&
            value.generation != 0 &&
            value.frameId != 0;
    }

    [[nodiscard]] constexpr bool FrameAckIdentityMatches(
        const FrameSlot& published,
        const FrameAck& ack) noexcept
    {
        return FrameSlotIdentityValid(published) &&
            ack.consumerPid != 0 &&
            ack.producerPid == published.producerPid &&
            ack.consumerPid == published.consumerPid &&
            ack.runGeneration == published.runGeneration &&
            ack.generation == published.generation &&
            ack.slot == published.slot;
    }

    [[nodiscard]] constexpr bool ConsumerAckCoversFrame(
        const FrameSlot& published,
        const FrameAck& ack) noexcept
    {
        return FrameAckIdentityMatches(published, ack) &&
            ack.completedFrameId >= published.frameId;
    }

    class IFrameProducer
    {
    public:
        virtual ~IFrameProducer() = default;
        virtual TransportKind kind() const noexcept = 0;
        virtual void invalidate() noexcept = 0;
        virtual bool publish(const PresentedFrame& frame, FrameSlot& outSlot) noexcept = 0;
    };

    class IFrameConsumer
    {
    public:
        virtual ~IFrameConsumer() = default;
        virtual TransportKind kind() const noexcept = 0;
        virtual void invalidate() noexcept = 0;
        virtual bool acquire(const PresentedFrame& frame, const FrameSlot& slot) noexcept = 0;
        virtual void acknowledge(const FrameAck& ack) noexcept = 0;
    };
}
