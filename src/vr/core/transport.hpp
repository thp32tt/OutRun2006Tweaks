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
        D3D11NativeShared = 4,
    };

    struct TransportIdentity
    {
        std::uint32_t producerPid{};
        std::uint32_t consumerPid{};
        std::uint32_t runGeneration{};
        std::uint32_t generation{};

        friend constexpr bool operator==(
            const TransportIdentity&, const TransportIdentity&) = default;
    };

    struct FrameAck
    {
        std::uint32_t producerPid{};
        std::uint32_t consumerPid{};
        std::uint32_t runGeneration{};
        std::uint32_t generation{};
        std::uint32_t slot{};
        std::uint64_t frameId{};
    };

    constexpr bool TransportIdentityValid(
        const TransportIdentity& identity) noexcept
    {
        return identity.producerPid != 0 &&
            identity.consumerPid != 0 &&
            identity.runGeneration != 0 &&
            identity.generation != 0;
    }

    constexpr bool TransportAckIdentityMatches(
        const FrameAck& ack,
        const TransportIdentity& identity) noexcept
    {
        return TransportIdentityValid(identity) &&
            ack.producerPid == identity.producerPid &&
            ack.consumerPid == identity.consumerPid &&
            ack.runGeneration == identity.runGeneration &&
            ack.generation == identity.generation;
    }

    constexpr bool TransportAckReleasesFrame(
        const FrameAck& ack,
        const TransportIdentity& identity,
        std::uint32_t slot,
        std::uint64_t frameId) noexcept
    {
        return frameId != 0 &&
            ack.slot == slot &&
            ack.frameId >= frameId &&
            TransportAckIdentityMatches(ack, identity);
    }

    struct FrameSlot
    {
        std::uint32_t generation{};
        std::uint32_t slot{};
        std::uint64_t frameId{};
        std::uintptr_t leftHandle{};
        std::uintptr_t rightHandle{};
        std::uint32_t width{};
        std::uint32_t height{};
        std::uint32_t format{};
    };

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
        // R117: acknowledgement is identity-complete by contract. A bare
        // frameId cannot prove producer/consumer PID, run generation,
        // transport generation or slot ownership, so it must never cross
        // the backend-neutral consumer boundary.
        virtual void acknowledge(const FrameAck& ack) noexcept = 0;
    };
}
