#include "vr/ipc/direct_ack_r13.hpp"
#include "vr/core/transport.hpp"

#include <cstdint>
#include <type_traits>

namespace
{
    using ConsumerAckSignature =
        void (OutRunVR::Core::IFrameConsumer::*)(
            const OutRunVR::Core::FrameAck&) noexcept;
    static_assert(
        std::is_same_v<
            decltype(&OutRunVR::Core::IFrameConsumer::acknowledge),
            ConsumerAckSignature>,
        "R117 consumer ACK contract must carry exact FrameAck identity");
}

int main()
{    using namespace OutRunVR::R13;
    DirectGpuAckState ack{};
    ack.hostPid = 10;
    ack.clientPid = 20;
    ack.runGeneration = 30;
    ack.transportGeneration = 40;

    if (!DirectGpuAckIdentityMatches(ack, 10, 20, 30, 40)) return 1;
    if (DirectGpuAckIdentityMatches(ack, 11, 20, 30, 40)) return 2;
    if (DirectGpuAckIdentityMatches(ack, 10, 21, 30, 40)) return 3;
    if (DirectGpuAckIdentityMatches(ack, 10, 20, 31, 40)) return 4;
    if (DirectGpuAckIdentityMatches(ack, 10, 20, 30, 41)) return 5;
    if (DirectGpuAckIdentityMatches(ack, 10, 20, 0, 40)) return 6;

    OutRunVR::Core::TransportIdentity nativeIdentity{};
    nativeIdentity.producerPid = 20;
    nativeIdentity.consumerPid = 10;
    nativeIdentity.runGeneration = 30;
    nativeIdentity.generation = 40;

    OutRunVR::Core::FrameAck nativeAck{};
    nativeAck.producerPid = 20;
    nativeAck.consumerPid = 10;
    nativeAck.runGeneration = 30;
    nativeAck.generation = 40;
    nativeAck.slot = 2;
    nativeAck.frameId = 100;

    if (!OutRunVR::Core::TransportAckReleasesFrame(
            nativeAck, nativeIdentity, 2, 100)) return 7;
    nativeAck.consumerPid = 11;
    if (OutRunVR::Core::TransportAckReleasesFrame(
            nativeAck, nativeIdentity, 2, 100)) return 8;
    nativeAck.consumerPid = 10;
    nativeAck.runGeneration = 31;
    if (OutRunVR::Core::TransportAckReleasesFrame(
            nativeAck, nativeIdentity, 2, 100)) return 9;
    nativeAck.runGeneration = 30;
    nativeAck.generation = 41;
    if (OutRunVR::Core::TransportAckReleasesFrame(
            nativeAck, nativeIdentity, 2, 100)) return 10;
    nativeAck.generation = 40;
    nativeAck.slot = 1;
    if (OutRunVR::Core::TransportAckReleasesFrame(
            nativeAck, nativeIdentity, 2, 100)) return 11;
    nativeAck.slot = 2;
    nativeAck.frameId = 99;
    if (OutRunVR::Core::TransportAckReleasesFrame(
            nativeAck, nativeIdentity, 2, 100)) return 12;
    nativeAck.frameId = 101;
    if (!OutRunVR::Core::TransportAckReleasesFrame(
            nativeAck, nativeIdentity, 2, 100)) return 13;

    return 0;
}
